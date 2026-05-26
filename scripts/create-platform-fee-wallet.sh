#!/bin/bash
# Create a dedicated BTX Start platform-fee wallet/address using a local btxd.
#
# This script never exports private keys and writes only public address metadata
# to platform-treasury.local.json. Do not commit wallet files, private keys, or
# seed material.

set -euo pipefail
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${PATH:-}"

WALLET_NAME="${BTX_START_WALLET_NAME:-btx-start-platform-fees}"
LABEL="${BTX_START_WALLET_LABEL:-platform-fees}"
OUTPUT_FILE="${BTX_START_WALLET_OUTPUT:-platform-treasury.local.json}"

log() { printf '\033[1;34m[treasury]\033[0m %s\n' "$*"; }
err() { printf '\033[1;31m[error]\033[0m %s\n' "$*" >&2; exit 1; }

command -v btx-cli >/dev/null 2>&1 || err "btx-cli not found. Install/run BTX node tooling first."

if ! btx-cli getblockchaininfo >/dev/null 2>&1; then
  err "btx-cli cannot reach btxd. Start btxd and unlock RPC before creating the platform wallet."
fi

if ! btx-cli listwallets | grep -F "\"${WALLET_NAME}\"" >/dev/null 2>&1; then
  log "creating wallet ${WALLET_NAME}"
  btx-cli createwallet "${WALLET_NAME}" >/dev/null
else
  log "wallet ${WALLET_NAME} already loaded"
fi

ADDRESS="$(btx-cli -rpcwallet="${WALLET_NAME}" getnewaddress "${LABEL}")"
case "$ADDRESS" in
  btx1z*) ;;
  *) err "created address does not look like a BTX btx1z address: ${ADDRESS}" ;;
esac

cat > "${OUTPUT_FILE}" <<JSON
{
  "name": "BTX Start Platform Treasury",
  "status": "created_locally",
  "wallet_name": "${WALLET_NAME}",
  "platform_fee_address": "${ADDRESS}",
  "platform_treasury_address": "${ADDRESS}",
  "platform_fee_balance_btx": "0.00000000",
  "balance_source": "Local wallet created by scripts/create-platform-fee-wallet.sh",
  "backend_policy": {
    "pool_fee_bps": 50,
    "fee_address": "${ADDRESS}",
    "treasury_address": "${ADDRESS}"
  }
}
JSON

log "created public platform fee address: ${ADDRESS}"
log "wrote public metadata to ${OUTPUT_FILE}"
log "next: copy the public address into platform-treasury.json and deploy backend policy:"
printf 'pool_fee_bps = 50\nfee_address = "%s"\ntreasury_address = "%s"\n' "$ADDRESS" "$ADDRESS"
log "backup and secure the wallet on the machine running btxd. Never commit wallet.dat or private keys."
