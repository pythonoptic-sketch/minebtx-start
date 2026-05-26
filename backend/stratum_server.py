"""Minimal stratum server entrypoint for stratum.drinknile.com:3333.

This is a guarded scaffold. It handles JSON-RPC framing, subscribe/authorize,
worker tracking, and rejected submit accounting. Production share acceptance
must add BTX matmul share validation before `ALLOW_UNVERIFIED_SHARE_ACCEPTANCE`
is ever enabled.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from dataclasses import dataclass
from typing import Any

from .repository import BackendRepository, ShareRecord
from .settings import BackendSettings

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
    ):
        self.reader = reader
        self.writer = writer
        self.repo = repo
        self.settings = settings
        self.identity: WorkerIdentity | None = None
        peer = writer.get_extra_info("peername")
        self.peer = f"{peer[0]}:{peer[1]}" if peer else "unknown"

    async def run(self) -> None:
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
                self.writer.write((json.dumps(response, separators=(",", ":")) + "\n").encode("utf-8"))
                await self.writer.drain()
        self.writer.close()
        await self.writer.wait_closed()

    async def handle_message(self, message: dict[str, Any]) -> dict[str, Any] | None:
        method = message.get("method")
        message_id = message.get("id")
        params = message.get("params") or []
        if method == "mining.subscribe":
            return {
                "id": message_id,
                "result": [[["mining.notify", "btx-start"]], "btx-start", 4],
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
                user_agent=self.peer,
            )
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
        if not self.settings.allow_unverified_share_acceptance:
            self.repo.record_share(
                ShareRecord(
                    payout_address=self.identity.payout_address,
                    worker_name=self.identity.worker_name,
                    job_id=job_id,
                    accepted=False,
                    reason="share validation not enabled",
                )
            )
            return {
                "id": message_id,
                "result": False,
                "error": [23, "share validation not enabled on this backend", None],
            }
        self.repo.record_share(
            ShareRecord(
                payout_address=self.identity.payout_address,
                worker_name=self.identity.worker_name,
                job_id=job_id,
                accepted=True,
            )
        )
        return {"id": message_id, "result": True, "error": None}


async def serve(settings: BackendSettings) -> None:
    settings.ensure_database_parent()
    repo = BackendRepository(settings.database_path)
    repo.init_db()

    async def handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        await StratumSession(reader, writer, repo, settings).run()

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
