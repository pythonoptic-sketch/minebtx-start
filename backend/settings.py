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
    pool_coinbase_address: str | None = None
    trial_days: int = 7
    trial_fee_bps: int = 0
    post_trial_fee_bps: int = 50
    pplns_window_hours: int = 24
    owned_backend_active: bool = False
    btx_rpc_url: str = "http://127.0.0.1:8332"
    btx_rpc_user: str | None = None
    btx_rpc_password: str | None = None
    pool_share_target_hex: str = "00000fffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
    stratum_job_refresh_s: int = 20
    stratum_notify_interval_s: int = 10
    share_validation_mode: str = "disabled"
    share_validation_solver_path: str = "~/.dexbtx-miner/bin/btx-gbt-solve"
    share_validation_backend: str = "cpu"
    share_validation_solver_threads: int = 2
    share_validation_batch_size: int = 2
    share_validation_max_tries: int = 8
    share_validation_max_seconds: float = 10.0
    block_submission_enabled: bool = False
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
    address_scan_enabled: bool = True
    address_scan_cache_ttl_s: int = 600
    verifier_default_max_cost_per_btx_usd: float = 1.00
    verifier_default_fee_bps: int = 50

    @classmethod
    def from_env(cls) -> "BackendSettings":
        return cls(
            database_path=os.environ.get("BTX_START_DATABASE_PATH", cls.database_path),
            public_stats_url=os.environ.get("PUBLIC_STATS_URL", cls.public_stats_url),
            public_stratum_host=os.environ.get("PUBLIC_STRATUM_HOST", cls.public_stratum_host),
            public_stratum_port=int(os.environ.get("PUBLIC_STRATUM_PORT", cls.public_stratum_port)),
            fee_address=os.environ.get("FEE_ADDRESS") or None,
            treasury_address=os.environ.get("TREASURY_ADDRESS") or None,
            pool_coinbase_address=(
                os.environ.get("POOL_COINBASE_ADDRESS")
                or os.environ.get("TREASURY_ADDRESS")
                or os.environ.get("FEE_ADDRESS")
                or None
            ),
            trial_days=int(os.environ.get("TRIAL_DAYS", cls.trial_days)),
            trial_fee_bps=int(os.environ.get("TRIAL_FEE_BPS", cls.trial_fee_bps)),
            post_trial_fee_bps=int(os.environ.get("POST_TRIAL_FEE_BPS", cls.post_trial_fee_bps)),
            pplns_window_hours=int(os.environ.get("PPLNS_WINDOW_HOURS", cls.pplns_window_hours)),
            owned_backend_active=_bool_env("OWNED_BACKEND_ACTIVE", cls.owned_backend_active),
            btx_rpc_url=os.environ.get("BTX_RPC_URL", cls.btx_rpc_url),
            btx_rpc_user=os.environ.get("BTX_RPC_USER") or None,
            btx_rpc_password=os.environ.get("BTX_RPC_PASSWORD") or None,
            pool_share_target_hex=os.environ.get("POOL_SHARE_TARGET_HEX", cls.pool_share_target_hex),
            stratum_job_refresh_s=int(os.environ.get("STRATUM_JOB_REFRESH_S", cls.stratum_job_refresh_s)),
            stratum_notify_interval_s=int(os.environ.get(
                "STRATUM_NOTIFY_INTERVAL_S",
                cls.stratum_notify_interval_s,
            )),
            share_validation_mode=os.environ.get(
                "SHARE_VALIDATION_MODE",
                cls.share_validation_mode,
            ),
            share_validation_solver_path=os.path.expanduser(os.environ.get(
                "SHARE_VALIDATION_SOLVER_PATH",
                cls.share_validation_solver_path,
            )),
            share_validation_backend=os.environ.get(
                "SHARE_VALIDATION_BACKEND",
                cls.share_validation_backend,
            ),
            share_validation_solver_threads=int(os.environ.get(
                "SHARE_VALIDATION_SOLVER_THREADS",
                cls.share_validation_solver_threads,
            )),
            share_validation_batch_size=int(os.environ.get(
                "SHARE_VALIDATION_BATCH_SIZE",
                cls.share_validation_batch_size,
            )),
            share_validation_max_tries=int(os.environ.get(
                "SHARE_VALIDATION_MAX_TRIES",
                cls.share_validation_max_tries,
            )),
            share_validation_max_seconds=float(os.environ.get(
                "SHARE_VALIDATION_MAX_SECONDS",
                cls.share_validation_max_seconds,
            )),
            block_submission_enabled=_bool_env(
                "BLOCK_SUBMISSION_ENABLED",
                cls.block_submission_enabled,
            ),
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
            address_scan_enabled=_bool_env(
                "ADDRESS_SCAN_ENABLED",
                cls.address_scan_enabled,
            ),
            address_scan_cache_ttl_s=int(os.environ.get(
                "ADDRESS_SCAN_CACHE_TTL_S",
                cls.address_scan_cache_ttl_s,
            )),
            verifier_default_max_cost_per_btx_usd=float(os.environ.get(
                "VERIFIER_DEFAULT_MAX_COST_PER_BTX_USD",
                cls.verifier_default_max_cost_per_btx_usd,
            )),
            verifier_default_fee_bps=int(os.environ.get(
                "VERIFIER_DEFAULT_FEE_BPS",
                cls.verifier_default_fee_bps,
            )),
        )

    def ensure_database_parent(self) -> None:
        Path(self.database_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
