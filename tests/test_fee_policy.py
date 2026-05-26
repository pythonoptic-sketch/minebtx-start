from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from fee_policy import FeePolicy, miner_account_key, parse_timestamp


class FeePolicyTest(unittest.TestCase):
    def test_fee_is_zero_during_first_seven_days(self) -> None:
        policy = FeePolicy(trial_days=7, trial_fee_bps=0, post_trial_fee_bps=50)
        first_share = datetime(2026, 5, 1, tzinfo=timezone.utc)
        now = datetime(2026, 5, 7, 23, 59, tzinfo=timezone.utc)

        split = policy.split_reward_sat(100_000_000, first_share, now)

        self.assertEqual(split["fee_bps"], 0)
        self.assertEqual(split["platform_fee_sat"], 0)
        self.assertEqual(split["miner_payout_sat"], 100_000_000)

    def test_fee_starts_after_trial_window(self) -> None:
        policy = FeePolicy(trial_days=7, trial_fee_bps=0, post_trial_fee_bps=50)
        first_share = datetime(2026, 5, 1, tzinfo=timezone.utc)
        now = datetime(2026, 5, 8, tzinfo=timezone.utc)

        split = policy.split_reward_sat(100_000_000, first_share, now)

        self.assertEqual(split["fee_bps"], 50)
        self.assertEqual(split["platform_fee_sat"], 500_000)
        self.assertEqual(split["miner_payout_sat"], 99_500_000)

    def test_trial_key_uses_payout_address_not_worker(self) -> None:
        self.assertEqual(miner_account_key(" btx1zabc "), "btx1zabc")

    def test_parse_z_timestamp(self) -> None:
        self.assertEqual(parse_timestamp("2026-05-01T00:00:00Z").tzinfo, timezone.utc)


if __name__ == "__main__":
    unittest.main()
