"""FastAPI app for api.drinknile.com."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any
from uuid import uuid4

try:
    from fastapi import FastAPI, Header, HTTPException, Request
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
except ImportError as exc:  # pragma: no cover - deployment dependency
    raise RuntimeError("Install backend requirements: pip install -r backend/requirements.txt") from exc

from .billing import CheckoutRequest, create_checkout_session, subscription_payload_from_event, verify_stripe_signature
from .btx_rpc import BtxRpcClient, BtxRpcError
from .fee_policy import FeePolicy
from .repository import BackendRepository
from .settings import BackendSettings

settings = BackendSettings.from_env()
settings.ensure_database_parent()
repo = BackendRepository(settings.database_path)
repo.init_db()
policy = FeePolicy(
    trial_days=settings.trial_days,
    trial_fee_bps=settings.trial_fee_bps,
    post_trial_fee_bps=settings.post_trial_fee_bps,
    fee_address=settings.fee_address,
    treasury_address=settings.treasury_address,
)
rpc = BtxRpcClient(settings.btx_rpc_url, settings.btx_rpc_user, settings.btx_rpc_password)

app = FastAPI(title="BTX Start Backend", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://drinknile.com", "https://www.drinknile.com"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


class CheckoutBody(BaseModel):
    email: str | None = None
    account_id: str | None = None


@app.get("/health")
def health() -> dict[str, Any]:
    node: dict[str, Any] = {"reachable": False}
    try:
        info = rpc.getblockchaininfo()
        node = {
            "reachable": True,
            "blocks": info.get("blocks"),
            "headers": info.get("headers"),
            "ibd": info.get("initialblockdownload"),
            "verification_progress": info.get("verificationprogress"),
        }
    except BtxRpcError as exc:
        node["error"] = str(exc)
    return {
        "ok": True,
        "owned_backend_active": settings.owned_backend_active,
        "btxd": node,
    }


@app.get("/stats")
def stats() -> dict[str, Any]:
    pool = repo.stats()
    node: dict[str, Any] = {
        "reachable": False,
        "blocks": None,
        "headers": None,
        "ibd": True,
        "verification_progress": 0,
        "network_hash_ps": None,
    }
    try:
        info = rpc.getblockchaininfo()
        node.update({
            "reachable": True,
            "blocks": info.get("blocks"),
            "headers": info.get("headers"),
            "ibd": info.get("initialblockdownload"),
            "verification_progress": info.get("verificationprogress"),
            "network_hash_ps": rpc.getnetworkhashps(),
        })
    except BtxRpcError:
        pass
    return {
        "pool": {
            "workers_active_now": pool["workers_active_now"],
            "workers_active_24h": pool["workers_active_now"],
            "shares_24h": pool["shares_24h"],
            "blocks_found_24h": pool["blocks_found_24h"],
            "pending_fee_sat": pool["pending_fee_sat"],
            "pending_miner_payout_sat": pool["pending_miner_payout_sat"],
        },
        "health": {
            "btxd": node,
            "shares_accepted": pool["shares_accepted_total"],
            "shares_rejected": pool["shares_rejected_total"],
        },
        "policy": {
            "owned_backend_active": settings.owned_backend_active,
            "status": "live" if settings.owned_backend_active else "provisioning",
            "fee_model": "per_wallet_trial_then_pool_fee",
            "fee_routing": "pool_payout_accounting",
            "account_key_scope": "payout_address",
            "trial_days": policy.trial_days,
            "trial_fee_bps": policy.trial_fee_bps,
            "post_trial_fee_bps": policy.post_trial_fee_bps,
            "pool_fee_bps": policy.post_trial_fee_bps,
            "treasury_address": policy.treasury_address,
            "fee_address": policy.fee_address,
            "stratum_endpoint": f"{settings.public_stratum_host}:{settings.public_stratum_port}",
            "stats_url": settings.public_stats_url,
        },
    }


@app.get("/dashboard/{payout_address}")
def dashboard(payout_address: str) -> dict[str, Any]:
    if not payout_address.startswith("btx1z"):
        raise HTTPException(status_code=400, detail="invalid BTX payout address")
    return repo.miner_dashboard(payout_address)


@app.post("/billing/checkout")
def checkout(body: CheckoutBody) -> dict[str, str]:
    if not settings.stripe_secret_key or not settings.stripe_price_id:
        raise HTTPException(status_code=503, detail="Stripe membership billing is not configured")
    account_id = body.account_id or str(uuid4())
    session = create_checkout_session(
        settings.stripe_secret_key,
        CheckoutRequest(
            account_id=account_id,
            customer_email=body.email,
            price_id=settings.stripe_price_id,
            success_url=settings.pro_success_url,
            cancel_url=settings.pro_cancel_url,
            trial_days=settings.trial_days,
        ),
    )
    return {"account_id": account_id, "checkout_url": session["url"], "session_id": session["id"]}


@app.post("/billing/webhook")
async def billing_webhook(request: Request, stripe_signature: str | None = Header(default=None)) -> dict[str, bool]:
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Stripe webhook secret is not configured")
    payload = await request.body()
    if not stripe_signature or not verify_stripe_signature(
        payload,
        stripe_signature,
        settings.stripe_webhook_secret,
    ):
        raise HTTPException(status_code=400, detail="invalid Stripe signature")
    event = json.loads(payload.decode("utf-8"))
    repo.record_event("stripe." + str(event.get("type", "unknown")), event)
    normalized = subscription_payload_from_event(event)
    if normalized:
        repo.upsert_subscription(**normalized)
    return {"ok": True}


@app.get("/policy")
def policy_payload() -> dict[str, Any]:
    return asdict(policy)
