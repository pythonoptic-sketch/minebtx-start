# Owned BTX Backend Cutover

This project does not currently contain the private DEXBTX pool backend. The
public `dexbtx/minebtx` repository only ships the miner client and installer.
The installer is intentionally pointed at `stratum.drinknile.com:3333` before
public mining launch. Do not mark the backend live, advertise active mining, or
enable fees until a first-party stratum pool, payout engine, stats API, BTX
wallet/node, and dedicated platform fee wallet are running.

## Non-Negotiable Wallet Separation

Your personal BTX mining address stays a miner payout address only.

It must not be used as:

- the pool fee address
- the platform treasury address
- the backend hot wallet
- the payout aggregation wallet
- a test address committed to git

Keep personal and rented-GPU payout addresses in a local file or env var:

```sh
export PROTECTED_PAYOUT_ADDRESSES='btx1z...personal...,btx1z...vast...'
```

Those values are intentionally ignored by git.

## First-Party Targets

The owned backend should expose:

```text
stratum.drinknile.com:3333
https://api.drinknile.com/stats
```

DNS records are documented in `backend/DNS.md`.

The public stats payload must include:

```json
{
  "policy": {
    "fee_model": "per_wallet_trial_then_pool_fee",
    "fee_routing": "pool_payout_accounting",
    "account_key_scope": "payout_address",
    "trial_days": 7,
    "trial_fee_bps": 0,
    "post_trial_fee_bps": 50,
    "pool_fee_bps": 50,
    "fee_address": "btx1z...",
    "treasury_address": "btx1z..."
  }
}
```

The launch policy is 0.00% for seven days per payout address, then 0.50% after
the trial. This must be enforced in backend payout accounting. The fee address
must be a dedicated public BTX Start address, not a personal payout address.

## Required Backend Components

Minimum production backend:

- synced `btxd` mainnet node with RPC locked to localhost/private network
- stratum server compatible with the current `dexbtx-miner` client
- per-worker share database keyed by `(payout_address, worker_name)`
- first-accepted-share table keyed by `payout_address` for the 7-day trial
- PPLNS accounting and payout journal
- platform-fee ledger that accumulates post-trial fees to the public fee wallet
- payout wallet with explicit operator approval flow
- public stats API
- per-wallet dashboard API
- monitoring for stale jobs, rejected shares, block propagation, RPC health,
  payout failures, and wallet balance

This repository now includes a deployable scaffold for those pieces:

- `backend/app.py` for `api.drinknile.com`
- `backend/stratum_server.py` for the TCP stratum entrypoint
- `backend/repository.py` and `backend/schema.sql` for accounting state
- `backend/payout_worker.py` for dry-run payout planning
- `backend/btx_rpc.py` for private `btxd` JSON-RPC calls
- `backend/billing.py` for optional Stripe membership hooks

The scaffold intentionally rejects submitted shares unless explicit development
mode is enabled. Real production launch still needs BTX matmul share validation
and block submission connected to the current job template.

The BTX docs describe `getblocktemplate` and `submitblock` as the pool-software
foundation. A production pool still needs coinbase construction, share target
validation, accepted-share accounting, block submission, maturity tracking, and
payout batching.

## Cutover Gate

Run this before changing `install.sh` or the site to point at the owned pool:

```sh
STATS_URL='https://api.drinknile.com/stats' \
STRATUM_HOST='stratum.drinknile.com' \
STRATUM_PORT='3333' \
EXPECTED_POOL_FEE_BPS='50' \
EXPECTED_TRIAL_DAYS='7' \
EXPECTED_TRIAL_FEE_BPS='0' \
EXPECTED_POST_TRIAL_FEE_BPS='50' \
EXPECTED_FEE_ADDRESS='btx1z...platform-fee...' \
EXPECTED_TREASURY_ADDRESS='btx1z...platform-treasury...' \
PROTECTED_PAYOUT_ADDRESSES='btx1z...personal...,btx1z...vast...' \
scripts/verify-owned-backend.sh
```

Only after that passes:

1. Set `platform-treasury.json` `owned_backend_active` and `active` to `true`.
2. Run installer preflight against the owned pool.
3. Run one miner with a new test payout address and verify shares appear in
   the first-party dashboard.

## Deployment Blocker In This Workspace

This machine currently has no `btxd`, no Docker/cloud deployment CLI for a VM,
no valid Vercel token, and no public pool backend source code. GitHub Pages can
host the website, but it cannot host a TCP stratum server or BTX wallet daemon.
