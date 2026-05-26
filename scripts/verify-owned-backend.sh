#!/bin/bash
set -euo pipefail

# Verifies that a first-party BTX Start backend is safe to cut over to.
# This script intentionally accepts protected miner payout addresses only via
# local environment variables so personal mining addresses never enter git.

PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"

STATS_URL="${STATS_URL:-https://api.drinknile.com/stats}"
STRATUM_HOST="${STRATUM_HOST:-stratum.drinknile.com}"
STRATUM_PORT="${STRATUM_PORT:-3333}"
EXPECTED_POOL_FEE_BPS="${EXPECTED_POOL_FEE_BPS:-0}"
EXPECTED_FEE_ADDRESS="${EXPECTED_FEE_ADDRESS:-}"
EXPECTED_TREASURY_ADDRESS="${EXPECTED_TREASURY_ADDRESS:-}"
PROTECTED_PAYOUT_ADDRESSES="${PROTECTED_PAYOUT_ADDRESSES:-}"

failures=0

fail() {
  printf '\033[1;31m[fail]\033[0m %s\n' "$*" >&2
  failures=$((failures + 1))
}

pass() {
  printf '\033[1;32m[pass]\033[0m %s\n' "$*"
}

need() {
  command -v "$1" >/dev/null 2>&1 || {
    fail "missing required command: $1"
    return 1
  }
}

need curl || true
need jq || true

if [ "$failures" -gt 0 ]; then
  exit 1
fi

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

if curl -fsSL "$STATS_URL" -o "$tmp"; then
  pass "stats API reachable: $STATS_URL"
else
  fail "stats API not reachable: $STATS_URL"
fi

if jq empty "$tmp" >/dev/null 2>&1; then
  pass "stats API returned valid JSON"
else
  fail "stats API did not return valid JSON"
fi

pool_fee_bps="$(jq -r '.policy.pool_fee_bps // empty' "$tmp" 2>/dev/null || true)"
fee_address="$(jq -r '.policy.fee_address // empty' "$tmp" 2>/dev/null || true)"
treasury_address="$(jq -r '.policy.treasury_address // empty' "$tmp" 2>/dev/null || true)"

if [ "$pool_fee_bps" = "$EXPECTED_POOL_FEE_BPS" ]; then
  pass "pool fee policy is ${pool_fee_bps} bps"
else
  fail "pool fee policy is ${pool_fee_bps:-missing} bps; expected ${EXPECTED_POOL_FEE_BPS}"
fi

if [ -n "$EXPECTED_FEE_ADDRESS" ]; then
  if [ "$fee_address" = "$EXPECTED_FEE_ADDRESS" ]; then
    pass "fee address matches expected first-party address"
  else
    fail "fee address does not match expected first-party address"
  fi
fi

if [ -n "$EXPECTED_TREASURY_ADDRESS" ]; then
  if [ "$treasury_address" = "$EXPECTED_TREASURY_ADDRESS" ]; then
    pass "treasury address matches expected first-party address"
  else
    fail "treasury address does not match expected first-party address"
  fi
fi

normalized_protected="$(printf '%s' "$PROTECTED_PAYOUT_ADDRESSES" | tr ',[:space:]' '\n' | sed '/^$/d')"
if [ -n "$normalized_protected" ]; then
  while IFS= read -r protected; do
    [ -n "$protected" ] || continue
    if [ "$fee_address" = "$protected" ]; then
      fail "fee address matches a protected personal payout address"
    fi
    if [ "$treasury_address" = "$protected" ]; then
      fail "treasury address matches a protected personal payout address"
    fi
  done <<EOF
$normalized_protected
EOF
  pass "protected personal payout addresses checked without publishing them"
else
  fail "PROTECTED_PAYOUT_ADDRESSES is empty; set it locally before cutover"
fi

if command -v nc >/dev/null 2>&1; then
  if nc -z -w 5 "$STRATUM_HOST" "$STRATUM_PORT" >/dev/null 2>&1 ||
      nc -z -G 5 "$STRATUM_HOST" "$STRATUM_PORT" >/dev/null 2>&1; then
    pass "stratum TCP reachable: ${STRATUM_HOST}:${STRATUM_PORT}"
  else
    fail "stratum TCP not reachable: ${STRATUM_HOST}:${STRATUM_PORT}"
  fi
else
  fail "missing required command: nc"
fi

if [ "$failures" -gt 0 ]; then
  printf '\nBackend is NOT safe for public installer cutover (%d failure(s)).\n' "$failures" >&2
  exit 1
fi

printf '\nBackend passes the public cutover checks.\n'
