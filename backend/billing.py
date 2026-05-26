"""Optional Stripe-backed membership helpers.

Membership must not gate base mining at launch. It should unlock optional Pro
dashboard features while base mining remains address-only.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class BillingError(RuntimeError):
    pass


def verify_stripe_signature(
    payload: bytes,
    signature_header: str,
    webhook_secret: str,
    *,
    tolerance_s: int = 300,
    now: int | None = None,
) -> bool:
    """Verify a Stripe webhook signature header.

    Stripe signs `timestamp.payload` using HMAC-SHA256 and sends one or more
    `v1=` signatures in the `Stripe-Signature` header.
    """

    parts: dict[str, list[str]] = {}
    for item in signature_header.split(","):
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        parts.setdefault(key, []).append(value)
    timestamp_values = parts.get("t")
    signatures = parts.get("v1", [])
    if not timestamp_values or not signatures:
        return False
    try:
        timestamp = int(timestamp_values[0])
    except ValueError:
        return False
    current = int(time.time()) if now is None else now
    if abs(current - timestamp) > tolerance_s:
        return False
    signed_payload = f"{timestamp}.".encode("utf-8") + payload
    expected = hmac.new(webhook_secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, candidate) for candidate in signatures)


@dataclass(frozen=True)
class CheckoutRequest:
    account_id: str
    customer_email: str | None
    price_id: str
    success_url: str
    cancel_url: str
    trial_days: int = 7


def create_checkout_session(secret_key: str, request: CheckoutRequest) -> dict[str, Any]:
    """Create a Stripe Checkout Session using Stripe's HTTPS API.

    The secret key must live only on the backend. The static website should
    call the backend endpoint, never Stripe directly with a secret key.
    """

    if not secret_key:
        raise BillingError("STRIPE_SECRET_KEY is not configured")
    form: list[tuple[str, str | int]] = [
        ("mode", "subscription"),
        ("line_items[0][price]", request.price_id),
        ("line_items[0][quantity]", 1),
        ("success_url", request.success_url),
        ("cancel_url", request.cancel_url),
        ("client_reference_id", request.account_id),
        ("subscription_data[trial_period_days]", request.trial_days),
        ("metadata[account_id]", request.account_id),
    ]
    if request.customer_email:
        form.append(("customer_email", request.customer_email))
    body = urlencode(form).encode("utf-8")
    http_request = Request(
        "https://api.stripe.com/v1/checkout/sessions",
        data=body,
        headers={
            "Authorization": f"Bearer {secret_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    try:
        with urlopen(http_request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise BillingError(f"Stripe checkout session creation failed: {exc}") from exc


def subscription_payload_from_event(event: dict[str, Any]) -> dict[str, Any] | None:
    """Extract normalized subscription state from common Stripe events."""

    event_type = event.get("type")
    obj = (event.get("data") or {}).get("object") or {}
    if event_type == "checkout.session.completed":
        account_id = obj.get("client_reference_id") or (obj.get("metadata") or {}).get("account_id")
        if not account_id:
            return None
        return {
            "account_id": account_id,
            "status": "trialing",
            "stripe_customer_id": obj.get("customer"),
            "stripe_subscription_id": obj.get("subscription"),
        }
    if event_type and event_type.startswith("customer.subscription."):
        account_id = (obj.get("metadata") or {}).get("account_id")
        if not account_id:
            return None
        return {
            "account_id": account_id,
            "status": obj.get("status", "unknown"),
            "stripe_customer_id": obj.get("customer"),
            "stripe_subscription_id": obj.get("id"),
            "trial_end": _unix_to_iso(obj.get("trial_end")),
            "current_period_end": _unix_to_iso(obj.get("current_period_end")),
        }
    return None


def _unix_to_iso(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(value)))
