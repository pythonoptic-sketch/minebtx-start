from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.stratum_server import parse_worker_identity


class StratumServerTest(unittest.TestCase):
    def test_parse_worker_identity(self) -> None:
        identity = parse_worker_identity("btx1z" + "a" * 52 + ".mac ultra")

        self.assertEqual(identity.payout_address, "btx1z" + "a" * 52)
        self.assertEqual(identity.worker_name, "mac-ultra")

    def test_reject_non_btx_worker(self) -> None:
        with self.assertRaises(ValueError):
            parse_worker_identity("not-a-wallet.worker")


if __name__ == "__main__":
    unittest.main()
