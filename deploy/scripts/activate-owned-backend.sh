#!/bin/sh
# Verify production backend and update public static JSON to active=true.
# Run from a clean repo checkout after DNS, btxd, fee wallet, API, and stratum
# are live.

set -eu
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${PATH:-}"

STATS_URL="${STATS_URL:-https://api.drinknile.com/stats}"
STRATUM_HOST="${STRATUM_HOST:-stratum.drinknile.com}"
STRATUM_PORT="${STRATUM_PORT:-3333}"
EXPECTED_POOL_FEE_BPS="${EXPECTED_POOL_FEE_BPS:-50}"
EXPECTED_TRIAL_DAYS="${EXPECTED_TRIAL_DAYS:-7}"
EXPECTED_TRIAL_FEE_BPS="${EXPECTED_TRIAL_FEE_BPS:-0}"
EXPECTED_POST_TRIAL_FEE_BPS="${EXPECTED_POST_TRIAL_FEE_BPS:-50}"
EXPECTED_FEE_ADDRESS="${EXPECTED_FEE_ADDRESS:-}"
EXPECTED_TREASURY_ADDRESS="${EXPECTED_TREASURY_ADDRESS:-$EXPECTED_FEE_ADDRESS}"

[ -n "$EXPECTED_FEE_ADDRESS" ] || { echo "EXPECTED_FEE_ADDRESS is required" >&2; exit 1; }

export STATS_URL
export STRATUM_HOST
export STRATUM_PORT
export EXPECTED_POOL_FEE_BPS
export EXPECTED_TRIAL_DAYS
export EXPECTED_TRIAL_FEE_BPS
export EXPECTED_POST_TRIAL_FEE_BPS
export EXPECTED_FEE_ADDRESS
export EXPECTED_TREASURY_ADDRESS

scripts/verify-owned-backend.sh

python3 - <<'PY'
import json
import os
from pathlib import Path

fee = os.environ["EXPECTED_FEE_ADDRESS"]
treasury = os.environ["EXPECTED_TREASURY_ADDRESS"]
stats_url = os.environ["STATS_URL"]
stratum = f'{os.environ["STRATUM_HOST"]}:{os.environ["STRATUM_PORT"]}'

treasury_path = Path("platform-treasury.json")
treasury_payload = json.loads(treasury_path.read_text())
treasury_payload.update({
    "status": "active",
    "active": True,
    "owned_backend_active": True,
    "target_stratum_endpoint": stratum,
    "target_stats_url": stats_url,
    "platform_fee_address": fee,
    "platform_treasury_address": treasury,
    "platform_fee_balance_btx": treasury_payload.get("platform_fee_balance_btx") or "0.00000000",
    "balance_source": "First-party BTX Start backend and wallet index",
})
treasury_path.write_text(json.dumps(treasury_payload, indent=2) + "\n")

snapshot_path = Path("stats-snapshot.json")
snapshot_payload = json.loads(snapshot_path.read_text())
snapshot_payload.setdefault("policy", {})
snapshot_payload["policy"].update({
    "owned_backend_active": True,
    "status": "active",
    "fee_address": fee,
    "treasury_address": treasury,
    "stratum_endpoint": stratum,
    "stats_url": stats_url,
})
snapshot_path.write_text(json.dumps(snapshot_payload, indent=2) + "\n")
PY

echo "updated platform-treasury.json and stats-snapshot.json"
echo "review, commit, and push these public activation changes"
