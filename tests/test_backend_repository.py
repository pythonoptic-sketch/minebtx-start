from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.fee_policy import FeePolicy
from backend.repository import BackendRepository, ShareRecord


class BackendRepositoryTest(unittest.TestCase):
    def test_share_starts_trial_and_reward_split_updates_balances(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = BackendRepository(Path(tmp) / "backend.sqlite3")
            repo.init_db()
            first_share = datetime(2026, 5, 1, tzinfo=timezone.utc)
            repo.record_share(
                ShareRecord(
                    payout_address="btx1z" + "a" * 52,
                    worker_name="rig-a",
                    job_id="job-1",
                    accepted=True,
                    created_at=first_share,
                )
            )

            split = repo.credit_reward(
                "btx1z" + "a" * 52,
                100_000_000,
                FeePolicy(trial_days=7, trial_fee_bps=0, post_trial_fee_bps=50),
                when=datetime(2026, 5, 8, tzinfo=timezone.utc),
            )

            self.assertEqual(split.fee_bps, 50)
            self.assertEqual(split.fee_sat, 500_000)
            dashboard = repo.miner_dashboard("btx1z" + "a" * 52)
            self.assertTrue(dashboard["known"])
            self.assertEqual(dashboard["balance"]["payable_sat"], 99_500_000)
            self.assertEqual(dashboard["shares"]["accepted"], 1)

            settled = repo.settle_payable_balances(txid="tx-test", dust_floor_sat=10_000)

            self.assertEqual(settled, 1)
            dashboard_after = repo.miner_dashboard("btx1z" + "a" * 52)
            self.assertEqual(dashboard_after["balance"]["payable_sat"], 0)

    def test_unknown_dashboard_is_safe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = BackendRepository(Path(tmp) / "backend.sqlite3")
            repo.init_db()
            dashboard = repo.miner_dashboard("btx1z" + "b" * 52)

            self.assertFalse(dashboard["known"])
            self.assertEqual(dashboard["balance"]["payable_sat"], 0)

    def test_pplns_reward_allocates_by_recent_accepted_shares(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = BackendRepository(Path(tmp) / "backend.sqlite3")
            repo.init_db()
            when = datetime(2026, 5, 10, tzinfo=timezone.utc)
            address_a = "btx1z" + "a" * 52
            address_b = "btx1z" + "b" * 52
            for index in range(3):
                repo.record_share(
                    ShareRecord(
                        payout_address=address_a,
                        worker_name="rig",
                        job_id=f"a-{index}",
                        accepted=True,
                        created_at=when,
                    )
                )
            repo.record_share(
                ShareRecord(
                    payout_address=address_b,
                    worker_name="rig",
                    job_id="b-1",
                    accepted=True,
                    created_at=when,
                )
            )

            splits = repo.credit_pplns_reward(
                100,
                FeePolicy(trial_days=7, trial_fee_bps=0, post_trial_fee_bps=50),
                when=when,
            )

            by_address = {split.payout_address: split for split in splits}
            self.assertEqual(by_address[address_a].gross_sat, 75)
            self.assertEqual(by_address[address_b].gross_sat, 25)


if __name__ == "__main__":
    unittest.main()
