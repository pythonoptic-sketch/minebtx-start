#!/bin/sh
# Generate /etc/btx-start/backend.env with random RPC credentials.
# Run on the backend host. Real fee/treasury addresses must be supplied.

set -eu
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${PATH:-}"

OUT="${OUT:-/etc/btx-start/backend.env}"
FEE_ADDRESS="${FEE_ADDRESS:-}"
TREASURY_ADDRESS="${TREASURY_ADDRESS:-$FEE_ADDRESS}"

if [ -z "$FEE_ADDRESS" ]; then
  echo "FEE_ADDRESS is required" >&2
  exit 1
fi

case "$FEE_ADDRESS" in
  btx1z*) ;;
  *) echo "FEE_ADDRESS must look like a btx1z address" >&2; exit 1 ;;
esac

if command -v openssl >/dev/null 2>&1; then
  RPC_USER="btxstart_$(openssl rand -hex 8)"
  RPC_PASS="$(openssl rand -hex 32)"
else
  RPC_USER="btxstart_$(python3 - <<'PY'
import secrets
print(secrets.token_hex(8))
PY
)"
  RPC_PASS="$(python3 - <<'PY'
import secrets
print(secrets.token_hex(32))
PY
)"
fi

OUT_DIR="$(dirname "$OUT")"
[ -d "$OUT_DIR" ] || install -d -m 0750 "$OUT_DIR"
umask 077
cat > "$OUT" <<EOF
BTX_START_DATABASE_PATH=/var/lib/btx-start/backend.sqlite3

PUBLIC_STRATUM_HOST=stratum.drinknile.com
PUBLIC_STRATUM_PORT=3333
PUBLIC_STATS_URL=https://api.drinknile.com/stats

OWNED_BACKEND_ACTIVE=false

TRIAL_DAYS=7
TRIAL_FEE_BPS=0
POST_TRIAL_FEE_BPS=50
PPLNS_WINDOW_HOURS=${PPLNS_WINDOW_HOURS:-24}
FEE_ADDRESS=${FEE_ADDRESS}
TREASURY_ADDRESS=${TREASURY_ADDRESS}
POOL_COINBASE_ADDRESS=${POOL_COINBASE_ADDRESS:-$TREASURY_ADDRESS}

BTX_RPC_URL=http://127.0.0.1:19334
BTX_RPC_USER=${RPC_USER}
BTX_RPC_PASSWORD=${RPC_PASS}

ALLOW_UNVERIFIED_SHARE_ACCEPTANCE=false

POOL_SHARE_TARGET_HEX=${POOL_SHARE_TARGET_HEX:-00000fffffffffffffffffffffffffffffffffffffffffffffffffffffffffff}
STRATUM_JOB_REFRESH_S=${STRATUM_JOB_REFRESH_S:-20}
STRATUM_NOTIFY_INTERVAL_S=${STRATUM_NOTIFY_INTERVAL_S:-10}
SHARE_VALIDATION_MODE=${SHARE_VALIDATION_MODE:-disabled}
SHARE_VALIDATION_SOLVER_PATH=${SHARE_VALIDATION_SOLVER_PATH:-/opt/btx-start/bin/btx-gbt-solve}
SHARE_VALIDATION_BACKEND=${SHARE_VALIDATION_BACKEND:-cpu}
SHARE_VALIDATION_SOLVER_THREADS=${SHARE_VALIDATION_SOLVER_THREADS:-2}
SHARE_VALIDATION_BATCH_SIZE=${SHARE_VALIDATION_BATCH_SIZE:-2}
SHARE_VALIDATION_MAX_TRIES=${SHARE_VALIDATION_MAX_TRIES:-8}
SHARE_VALIDATION_MAX_SECONDS=${SHARE_VALIDATION_MAX_SECONDS:-10}
BLOCK_SUBMISSION_ENABLED=${BLOCK_SUBMISSION_ENABLED:-false}

NETWORK_AGENT_PEER_URL=https://peers.minebtx.com/api/peer_list?relaxed=true&n=50
NETWORK_AGENT_INTERVAL_S=60
NETWORK_AGENT_SNAPSHOT_PATH=/var/lib/btx-start/network-agent-snapshot.json
NETWORK_AGENT_MIN_SCORE=0.70
NETWORK_AGENT_APPLY_PEERS=false

STRIPE_SECRET_KEY=${STRIPE_SECRET_KEY:-}
STRIPE_WEBHOOK_SECRET=${STRIPE_WEBHOOK_SECRET:-}
STRIPE_PRICE_ID=${STRIPE_PRICE_ID:-}
PRO_SUCCESS_URL=https://drinknile.com/#track
PRO_CANCEL_URL=https://drinknile.com/#operating-model
EOF

chmod 0600 "$OUT"
echo "wrote $OUT"
echo "BTX RPC user: ${RPC_USER}"
