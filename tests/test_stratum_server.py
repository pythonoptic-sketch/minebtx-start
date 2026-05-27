from __future__ import annotations

from pathlib import Path
import sys
import asyncio
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.repository import BackendRepository
from backend.settings import BackendSettings
from backend.fee_policy import FeePolicy
from backend.share_validation import ValidationResult
from backend.stratum_jobs import PoolJob, job_from_block_template, job_from_matmul_challenge
from backend.stratum_server import StratumSession, parse_worker_identity


class _Writer:
    def get_extra_info(self, name: str):
        if name == "peername":
            return ("127.0.0.1", 12345)
        return None


class _Validator:
    async def validate(self, job, share):
        return ValidationResult(True, difficulty=job.share_work)


class _Rpc:
    def submitblock(self, block_hex):
        return None


class StratumServerTest(unittest.TestCase):
    def test_parse_worker_identity(self) -> None:
        identity = parse_worker_identity("btx1z" + "a" * 52 + ".mac ultra")

        self.assertEqual(identity.payout_address, "btx1z" + "a" * 52)
        self.assertEqual(identity.worker_name, "mac-ultra")

    def test_reject_non_btx_worker(self) -> None:
        with self.assertRaises(ValueError):
            parse_worker_identity("not-a-wallet.worker")

    def test_job_from_matmul_challenge_builds_notify_payload(self) -> None:
        job = job_from_matmul_challenge(
            {
                "height": 123,
                "bits": "1d17c609",
                "target": "00" + "f" * 62,
                "header_context": {
                    "version": 536870912,
                    "previousblockhash": "a" * 64,
                    "merkleroot": "b" * 64,
                    "time": 1779672814,
                    "bits": "1d17c609",
                    "nonce64_start": 0,
                    "matmul_dim": 512,
                    "seed_a": "c" * 64,
                    "seed_b": "d" * 64,
                },
                "matmul": {"n": 512, "b": 16, "r": 8},
            },
            share_target_hex="00000" + "f" * 59,
        )

        notify = job.notify_params(clean_jobs=True, nonce64_start=99)

        self.assertEqual(notify[0], "123:" + "a" * 16 + ":1779672814")
        self.assertEqual(notify[8]["block_height"], 123)
        self.assertEqual(notify[8]["nonce64_start"], 99)

    def test_job_from_block_template_uses_real_merkle_root(self) -> None:
        job = job_from_block_template(
            {
                "height": 123,
                "coinbasevalue": 50_000_000,
                "default_witness_commitment": "6a24aa21a9ed" + "00" * 32,
                "transactions": [],
                "version": 536870912,
                "previousblockhash": "a" * 64,
                "curtime": 1779672814,
                "bits": "1d17c609",
                "target": "00" + "f" * 62,
                "seed_a": "c" * 64,
                "seed_b": "d" * 64,
                "matmul_n": 512,
                "matmul_b": 16,
                "matmul_r": 8,
            },
            share_target_hex="00000" + "f" * 59,
            coinbase_address="btx1z" + "e" * 52,
            address_script_pubkey_hex="0014" + "11" * 20,
        )

        self.assertNotEqual(job.merkleroot, "0" * 64)
        self.assertEqual(job.block_template["_merkle_root_hex_be"], job.merkleroot)

    def test_submit_accepted_share_records_accounting(self) -> None:
        async def run_case() -> None:
            with tempfile.TemporaryDirectory() as tmp:
                repo = BackendRepository(Path(tmp) / "backend.sqlite3")
                repo.init_db()
                settings = BackendSettings(database_path=str(Path(tmp) / "backend.sqlite3"))
                session = StratumSession(
                    asyncio.StreamReader(),
                    _Writer(),
                    repo,
                    settings,
                    job_manager=type("JobManager", (), {})(),
                    share_validator=_Validator(),
                    rpc=_Rpc(),
                    policy=FeePolicy(),
                )
                address = "btx1z" + "a" * 52
                session.identity = parse_worker_identity(address + ".mac")
                session.job_manager.current_job = PoolJob(
                    job_id="job-1",
                    version=1,
                    previousblockhash="a" * 64,
                    merkleroot="b" * 64,
                    time=100,
                    bits="1d17c609",
                    block_target="00" + "f" * 62,
                    share_target="00000" + "f" * 59,
                    height=2,
                    seed_a="c" * 64,
                    seed_b="d" * 64,
                    matmul_n=512,
                    matmul_b=16,
                    matmul_r=8,
                    epsilon_bits=18,
                    created_at=0,
                )

                response = await session._handle_submit(
                    10,
                    [address + ".mac", "job-1", "00000000", "00000064", "0000000000000001"],
                )

                self.assertTrue(response["result"])
                dashboard = repo.miner_dashboard(address)
                self.assertEqual(dashboard["shares"]["accepted"], 1)

        asyncio.run(run_case())


if __name__ == "__main__":
    unittest.main()
