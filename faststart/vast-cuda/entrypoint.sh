#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${BTX_ADDRESS:-}" ]]; then
  echo "BTX_ADDRESS is required. Pass your public btx1z payout address as an environment variable." >&2
  exit 64
fi

WORKER="${BTX_WORKER:-vast-${HOSTNAME:-cuda}}"
CONFIG_PATH="${HOME}/.dexbtx-miner/config.yaml"

if [[ "${BTX_FASTSTART_SKIP_INSTALL:-0}" != "1" || ! -f "${CONFIG_PATH}" ]]; then
  curl -fsSL "${INSTALLER_URL:-https://drinknile.com/install.sh}" | bash -s -- \
    --address "${BTX_ADDRESS}" \
    --worker "${WORKER}" \
    --solver-backend "${BTX_SOLVER_BACKEND:-cuda}"
fi

if [[ -n "${BTX_RENTAL_HOURLY_USD:-}" && -n "${BTX_MEASURED_NPS:-}" && -n "${BTX_NETWORK_NPS:-}" ]]; then
  dexbtx-miner verify-rental \
    --backend cuda \
    --measured-nps "${BTX_MEASURED_NPS}" \
    --network-nps "${BTX_NETWORK_NPS}" \
    --hourly-usd "${BTX_RENTAL_HOURLY_USD}" \
    --max-cost-per-btx "${BTX_MAX_COST_PER_BTX_USD:-1.00}" \
    --fee-bps "${BTX_PLATFORM_FEE_BPS:-50}"
else
  echo "Skipping rental verifier. Set BTX_MEASURED_NPS, BTX_NETWORK_NPS, and BTX_RENTAL_HOURLY_USD to gate this rental." >&2
fi

exec dexbtx-miner --config "${CONFIG_PATH}"
