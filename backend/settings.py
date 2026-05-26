"""Environment-driven backend settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class BackendSettings:
    database_path: str = "backend/backend.local.sqlite3"
    public_stats_url: str = "https://api.drinknile.com/stats"
    public_stratum_host: str = "stratum.drinknile.com"
    public_stratum_port: int = 3333
    fee_address: str | None = None
    treasury_address: str | None = None
    trial_days: int = 7
    trial_fee_bps: int = 0
    post_trial_fee_bps: int = 50
    owned_backend_active: bool = False
    btx_rpc_url: str = "http://127.0.0.1:8332"
    btx_rpc_user: str | None = None
    btx_rpc_password: str | None = None
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    stripe_price_id: str | None = None
    pro_success_url: str = "https://drinknile.com/#track"
    pro_cancel_url: str = "https://drinknile.com/#operating-model"
    allow_unverified_share_acceptance: bool = False
    network_agent_peer_url: str = "https://peers.minebtx.com/api/peer_list?relaxed=true&n=50"
    network_agent_interval_s: int = 60
    network_agent_snapshot_path: str = "backend/network-agent.local.json"
    network_agent_min_score: float = 0.70
    network_agent_apply_peers: bool = False

    @classmethod
    def from_env(cls) -> "BackendSettings":
        return cls(
            database_path=os.environ.get("BTX_START_DATABASE_PATH", cls.database_path),
            public_stats_url=os.environ.get("PUBLIC_STATS_URL", cls.public_stats_url),
            public_stratum_host=os.environ.get("PUBLIC_STRATUM_HOST", cls.public_stratum_host),
            public_stratum_port=int(os.environ.get("PUBLIC_STRATUM_PORT", cls.public_stratum_port)),
            fee_address=os.environ.get("FEE_ADDRESS") or None,
            treasury_address=os.environ.get("TREASURY_ADDRESS") or None,
            trial_days=int(os.environ.get("TRIAL_DAYS", cls.trial_days)),
            trial_fee_bps=int(os.environ.get("TRIAL_FEE_BPS", cls.trial_fee_bps)),
            post_trial_fee_bps=int(os.environ.get("POST_TRIAL_FEE_BPS", cls.post_trial_fee_bps)),
            owned_backend_active=_bool_env("OWNED_BACKEND_ACTIVE", cls.owned_backend_active),
            btx_rpc_url=os.environ.get("BTX_RPC_URL", cls.btx_rpc_url),
            btx_rpc_user=os.environ.get("BTX_RPC_USER") or None,
            btx_rpc_password=os.environ.get("BTX_RPC_PASSWORD") or None,
            stripe_secret_key=os.environ.get("STRIPE_SECRET_KEY") or None,
            stripe_webhook_secret=os.environ.get("STRIPE_WEBHOOK_SECRET") or None,
            stripe_price_id=os.environ.get("STRIPE_PRICE_ID") or None,
            pro_success_url=os.environ.get("PRO_SUCCESS_URL", cls.pro_success_url),
            pro_cancel_url=os.environ.get("PRO_CANCEL_URL", cls.pro_cancel_url),
            allow_unverified_share_acceptance=_bool_env("ALLOW_UNVERIFIED_SHARE_ACCEPTANCE", False),
            network_agent_peer_url=os.environ.get(
                "NETWORK_AGENT_PEER_URL",
                cls.network_agent_peer_url,
            ),
            network_agent_interval_s=int(os.environ.get(
                "NETWORK_AGENT_INTERVAL_S",
                cls.network_agent_interval_s,
            )),
            network_agent_snapshot_path=os.environ.get(
                "NETWORK_AGENT_SNAPSHOT_PATH",
                cls.network_agent_snapshot_path,
            ),
            network_agent_min_score=float(os.environ.get(
                "NETWORK_AGENT_MIN_SCORE",
                cls.network_agent_min_score,
            )),
            network_agent_apply_peers=_bool_env(
                "NETWORK_AGENT_APPLY_PEERS",
                cls.network_agent_apply_peers,
            ),
        )

    def ensure_database_parent(self) -> None:
        Path(self.database_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
