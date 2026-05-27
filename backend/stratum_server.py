"""Stratum server entrypoint for stratum.drinknile.com:3333.

This server now emits live MatMul jobs from btxd and records worker/share state.
Share acceptance is still gated by a real validator. Keep
SHARE_VALIDATION_MODE=disabled in public production until a patched solver or
in-process verifier is present on the backend host.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import secrets
from dataclasses import dataclass
from typing import Any

from .block_builder import build_block_hex
from .btx_rpc import BtxRpcClient
from .fee_policy import FeePolicy
from .repository import BackendRepository, ShareRecord
from .settings import BackendSettings
from .share_validation import SubmittedShare, build_share_validator
from .stratum_jobs import PoolJob, StratumJobManager

ADDRESS_RE = re.compile(r"^btx1z[0-9a-zA-Z]{20,}$")


@dataclass(frozen=True)
class WorkerIdentity:
    payout_address: str
    worker_name: str


def parse_worker_identity(value: str) -> WorkerIdentity:
    if "." in value:
        payout_address, worker_name = value.split(".", 1)
    else:
        payout_address, worker_name = value, "default"
    payout_address = payout_address.strip()
    worker_name = re.sub(r"[^a-zA-Z0-9._-]", "-", (worker_name.strip() or "default"))
    if not ADDRESS_RE.match(payout_address):
        raise ValueError("worker name must start with a btx1z payout address")
    return WorkerIdentity(payout_address, worker_name)


class StratumSession:
    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        repo: BackendRepository,
        settings: BackendSettings,
        job_manager: StratumJobManager,
        share_validator: Any,
        rpc: BtxRpcClient,
        policy: FeePolicy,
    ):
        self.reader = reader
        self.writer = writer
        self.repo = repo
        self.settings = settings
        self.job_manager = job_manager
        self.share_validator = share_validator
        self.rpc = rpc
        self.policy = policy
        self.identity: WorkerIdentity | None = None
        self.agent_string: str | None = None
        self.extranonce1 = secrets.token_hex(4)
        self.extranonce2_size = 4
        self._notify_after_response = False
        self._last_notified_job_id: str | None = None
        self._submitted: set[tuple[str, str, str]] = set()
        self._nonce_start = secrets.randbits(64)
        peer = writer.get_extra_info("peername")
        self.peer = f"{peer[0]}:{peer[1]}" if peer else "unknown"

    async def run(self) -> None:
        notify_task = asyncio.create_task(self._notify_loop())
        try:
            while not self.reader.at_eof():
                line = await self.reader.readline()
                if not line:
                    break
                try:
                    message = json.loads(line.decode("utf-8"))
                    response = await self.handle_message(message)
                except Exception as exc:
                    response = {"id": None, "result": None, "error": [20, str(exc), None]}
                if response is not None:
                    await self._send(response)
                if self._notify_after_response:
                    self._notify_after_response = False
                    await self._send_initial_job()
        finally:
            notify_task.cancel()
            try:
                await notify_task
            except (asyncio.CancelledError, Exception):
                pass
            self.writer.close()
            await self.writer.wait_closed()

    async def handle_message(self, message: dict[str, Any]) -> dict[str, Any] | None:
        method = message.get("method")
        message_id = message.get("id")
        params = message.get("params") or []
        if method == "mining.subscribe":
            self.agent_string = str(params[0]) if params else None
            return {
                "id": message_id,
                "result": [[["mining.notify", self.extranonce1]], self.extranonce1, self.extranonce2_size],
                "error": None,
            }
        if method == "mining.authorize":
            worker = str(params[0]) if params else ""
            try:
                self.identity = parse_worker_identity(worker)
            except ValueError as exc:
                return {"id": message_id, "result": False, "error": [24, str(exc), None]}
            self.repo.touch_worker(
                self.identity.payout_address,
                self.identity.worker_name,
                user_agent=self.agent_string or self.peer,
            )
            self._notify_after_response = True
            return {"id": message_id, "result": True, "error": None}
        if method == "mining.submit":
            return await self._handle_submit(message_id, params)
        if method in {"mining.configure", "mining.extranonce.subscribe"}:
            return {"id": message_id, "result": {}, "error": None}
        return {"id": message_id, "result": None, "error": [20, f"unsupported method {method}", None]}

    async def _handle_submit(self, message_id: Any, params: list[Any]) -> dict[str, Any]:
        if self.identity is None:
            return {"id": message_id, "result": False, "error": [24, "authorize first", None]}
        job_id = str(params[1]) if len(params) > 1 else "unknown"
        if len(params) < 5:
            return {"id": message_id, "result": False, "error": [20, "bad submit params", None]}
        worker = str(params[0])
        try:
            submitted_identity = parse_worker_identity(worker)
        except ValueError as exc:
            return {"id": message_id, "result": False, "error": [24, str(exc), None]}
        if submitted_identity != self.identity:
            return {"id": message_id, "result": False, "error": [24, "worker identity changed", None]}
        extranonce2 = str(params[2])
        ntime_hex = str(params[3])
        nonce_hex = str(params[4])
        submission_key = (job_id, extranonce2, nonce_hex)
        if submission_key in self._submitted:
            self.repo.record_share(
                ShareRecord(
                    payout_address=self.identity.payout_address,
                    worker_name=self.identity.worker_name,
                    job_id=job_id,
                    accepted=False,
                    reason="duplicate share",
                )
            )
            return {"id": message_id, "result": False, "error": [22, "duplicate share", None]}
        self._submitted.add(submission_key)
        job = self.job_manager.current_job
        if job is None or job.job_id != job_id:
            self.repo.record_share(
                ShareRecord(
                    payout_address=self.identity.payout_address,
                    worker_name=self.identity.worker_name,
                    job_id=job_id,
                    accepted=False,
                    reason="stale job",
                )
            )
            return {"id": message_id, "result": False, "error": [21, "stale job", None]}
        try:
            share = SubmittedShare(
                job_id=job_id,
                nonce=int(nonce_hex, 16),
                ntime=int(ntime_hex, 16),
                extranonce2=extranonce2,
            )
        except ValueError:
            self.repo.record_share(
                ShareRecord(
                    payout_address=self.identity.payout_address,
                    worker_name=self.identity.worker_name,
                    job_id=job_id,
                    accepted=False,
                    reason="bad nonce or ntime",
                )
            )
            return {"id": message_id, "result": False, "error": [20, "bad nonce or ntime", None]}
        if self.settings.allow_unverified_share_acceptance:
            validation = None
            accepted = True
            reason = None
            is_block = False
            difficulty = job.share_work
        else:
            validation = await self.share_validator.validate(job, share)
            accepted = validation.accepted
            reason = validation.reason
            is_block = validation.is_block
            difficulty = validation.difficulty
        if not accepted:
            self.repo.record_share(
                ShareRecord(
                    payout_address=self.identity.payout_address,
                    worker_name=self.identity.worker_name,
                    job_id=job_id,
                    accepted=False,
                    difficulty=difficulty,
                    reason=reason or "share rejected",
                )
            )
            return {
                "id": message_id,
                "result": False,
                "error": [23, reason or "share rejected", None],
            }
        self.repo.record_share(
            ShareRecord(
                payout_address=self.identity.payout_address,
                worker_name=self.identity.worker_name,
                job_id=job_id,
                accepted=True,
                is_block=is_block,
                difficulty=difficulty,
            )
        )
        if is_block:
            await self._submit_block_candidate(job, share, validation, nonce_hex)
        return {"id": message_id, "result": True, "error": None}

    async def _submit_block_candidate(
        self,
        job: PoolJob,
        share: SubmittedShare,
        validation: Any,
        nonce_hex: str,
    ) -> None:
        raw = getattr(validation, "raw_output", None) or {}
        digest_hex = raw.get("matmul_digest") or raw.get("digest") or getattr(validation, "digest_hex", None)
        matrix_c_data_hex = raw.get("matrix_c_data_hex")
        event = {
            "job_id": job.job_id,
            "payout_address": self.identity.payout_address if self.identity else None,
            "worker_name": self.identity.worker_name if self.identity else None,
            "nonce_hex": nonce_hex,
            "digest_hex": digest_hex,
            "block_submission_enabled": self.settings.block_submission_enabled,
            "submitted": False,
        }
        if not self.settings.block_submission_enabled:
            event["reason"] = "block submission disabled"
            self.repo.record_event("stratum.block_candidate", event)
            return
        if not job.block_template or not job.address_script_pubkey_hex:
            event["reason"] = "missing block template or coinbase script"
            self.repo.record_event("stratum.block_candidate", event)
            return
        if not digest_hex or not matrix_c_data_hex:
            event["reason"] = "validator did not return block payload data"
            self.repo.record_event("stratum.block_candidate", event)
            return
        try:
            block_hex = build_block_hex(
                job.block_template,
                address_script_pubkey_hex=job.address_script_pubkey_hex,
                nonce64=share.nonce,
                matmul_digest_hex=digest_hex,
                matrix_c_data_hex=matrix_c_data_hex,
            )
            submit_result = await asyncio.to_thread(self.rpc.submitblock, block_hex)
        except Exception as exc:
            event["reason"] = f"submit error: {exc}"
            self.repo.record_event("stratum.block_candidate", event)
            return
        event["submitted"] = submit_result is None
        event["submit_result"] = submit_result
        event["coinbase_address"] = job.coinbase_address
        event["height"] = job.height
        self.repo.record_event("stratum.block_candidate", event)
        if submit_result is None:
            await asyncio.to_thread(
                self.repo.credit_pplns_reward,
                int(job.block_template["coinbasevalue"]),
                self.policy,
                window_hours=self.settings.pplns_window_hours,
            )

    async def _notify_loop(self) -> None:
        while True:
            await asyncio.sleep(max(1, self.settings.stratum_notify_interval_s))
            if self.identity is None:
                continue
            try:
                job = await self.job_manager.get_job()
            except Exception:
                continue
            if job.job_id != self._last_notified_job_id:
                await self._send_job(job, clean_jobs=True)

    async def _send_initial_job(self) -> None:
        await self._send({"id": None, "method": "mining.set_difficulty", "params": [1.0]})
        job = await self.job_manager.get_job(force=True)
        await self._send_job(job, clean_jobs=True)

    async def _send_job(self, job: PoolJob, *, clean_jobs: bool) -> None:
        await self._send({
            "id": None,
            "method": "mining.notify",
            "params": job.notify_params(clean_jobs=clean_jobs, nonce64_start=self._next_nonce_start()),
        })
        self._last_notified_job_id = job.job_id

    def _next_nonce_start(self) -> int:
        # Give each session a different starting area. The miner advances its
        # own nonce window from there; this avoids everyone beginning at zero.
        self._nonce_start = (self._nonce_start + 0x1_0000_0000) & 0xFFFF_FFFF_FFFF_FFFF
        return self._nonce_start

    async def _send(self, payload: dict[str, Any]) -> None:
        self.writer.write((json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8"))
        await self.writer.drain()


async def serve(settings: BackendSettings) -> None:
    settings.ensure_database_parent()
    repo = BackendRepository(settings.database_path)
    repo.init_db()
    rpc = BtxRpcClient(settings.btx_rpc_url, settings.btx_rpc_user, settings.btx_rpc_password)
    job_manager = StratumJobManager(
        rpc,
        share_target_hex=settings.pool_share_target_hex,
        refresh_interval_s=settings.stratum_job_refresh_s,
        coinbase_address=settings.pool_coinbase_address,
    )
    share_validator = build_share_validator(settings)
    policy = FeePolicy(
        trial_days=settings.trial_days,
        trial_fee_bps=settings.trial_fee_bps,
        post_trial_fee_bps=settings.post_trial_fee_bps,
        fee_address=settings.fee_address,
        treasury_address=settings.treasury_address,
    )

    async def handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        await StratumSession(reader, writer, repo, settings, job_manager, share_validator, rpc, policy).run()

    server = await asyncio.start_server(handler, host="0.0.0.0", port=settings.public_stratum_port)
    async with server:
        await server.serve_forever()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the BTX Start stratum backend")
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()
    settings = BackendSettings.from_env()
    if args.port is not None:
        settings = BackendSettings(**{**settings.__dict__, "public_stratum_port": args.port})
    asyncio.run(serve(settings))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
