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
FEE_ADDRESS=${FEE_ADDRESS}
TREASURY_ADDRESS=${TREASURY_ADDRESS}

BTX_RPC_URL=http://127.0.0.1:8332
BTX_RPC_USER=${RPC_USER}
BTX_RPC_PASSWORD=${RPC_PASS}

ALLOW_UNVERIFIED_SHARE_ACCEPTANCE=false

STRIPE_SECRET_KEY=${STRIPE_SECRET_KEY:-}
STRIPE_WEBHOOK_SECRET=${STRIPE_WEBHOOK_SECRET:-}
STRIPE_PRICE_ID=${STRIPE_PRICE_ID:-}
PRO_SUCCESS_URL=https://drinknile.com/#track
PRO_CANCEL_URL=https://drinknile.com/#operating-model
EOF

chmod 0600 "$OUT"
echo "wrote $OUT"
echo "BTX RPC user: ${RPC_USER}"
