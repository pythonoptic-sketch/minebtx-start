from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.economics import quote_verified_compute
from backend.repository import BackendRepository


class EconomicsTest(unittest.TestCase):
    def test_verified_compute_rejects_when_buying_is_cheaper(self) -> None:
        quote = quote_verified_compute(
            measured_nps=76_000,
            network_nps=2_338_067,
            hourly_usd=0.50,
            fee_bps=50,
            max_cost_per_btx_usd=1.00,
            reference_buy_price_usd=0.01,
        )

        self.assertTrue(quote.buy_beats_mine)
        self.assertIn("buy", quote.recommendation)

    def test_verified_compute_clears_cost_gate(self) -> None:
        quote = quote_verified_compute(
            measured_nps=76_000,
            network_nps=2_338_067,
            hourly_usd=0.01,
            fee_bps=50,
            max_cost_per_btx_usd=1.00,
        )

        self.assertTrue(quote.clears_cost_gate)
        self.assertLess(quote.cost_per_btx_usd or 999, 1.00)


class AddressScanCacheTest(unittest.TestCase):
    def test_address_scan_cache_round_trips(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = BackendRepository(Path(tmp) / "backend.sqlite3")
            repo.init_db()
            address = "btx1z" + "a" * 52

            repo.record_address_balance_scan(
                address,
                source="btxd.scantxoutset",
                payload={"address": address, "total_btx": 1.25, "unspent_count": 2},
            )

            cached = repo.get_address_balance_scan(address, max_age_seconds=60)

            self.assertIsNotNone(cached)
            self.assertEqual(cached["address"], address)
            self.assertEqual(cached["total_btx"], 1.25)
            self.assertTrue(cached["cached"])


if __name__ == "__main__":
    unittest.main()
