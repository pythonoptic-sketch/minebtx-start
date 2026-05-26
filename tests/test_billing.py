from __future__ import annotations

import hashlib
import hmac
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.billing import subscription_payload_from_event, verify_stripe_signature


class BillingTest(unittest.TestCase):
    def test_stripe_signature_verification(self) -> None:
        payload = b'{"type":"checkout.session.completed"}'
        secret = "whsec_test"
        timestamp = 1_770_000_000
        signed = f"{timestamp}.".encode("utf-8") + payload
        digest = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
        header = f"t={timestamp},v1={digest}"

        self.assertTrue(
            verify_stripe_signature(payload, header, secret, now=timestamp)
        )
        self.assertFalse(
            verify_stripe_signature(payload, header, "wrong", now=timestamp)
        )

    def test_checkout_event_normalizes_subscription_identity(self) -> None:
        event = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "client_reference_id": "acct_123",
                    "customer": "cus_123",
                    "subscription": "sub_123",
                }
            },
        }

        payload = subscription_payload_from_event(event)

        self.assertEqual(payload["account_id"], "acct_123")
        self.assertEqual(payload["status"], "trialing")
        self.assertEqual(payload["stripe_subscription_id"], "sub_123")


if __name__ == "__main__":
    unittest.main()
