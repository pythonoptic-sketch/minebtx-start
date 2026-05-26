# Owned BTX Backend Cutover

This project does not currently contain the private DEXBTX pool backend. The
public `dexbtx/minebtx` repository only ships the miner client and installer.
Do not switch visitors to `stratum.drinknile.com:3333` until a first-party
stratum pool, payout engine, stats API, and BTX wallet/node are running.

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

The public stats payload must include:

```json
{
  "policy": {
    "pool_fee_bps": 0,
    "fee_address": "btx1z...",
    "treasury_address": "btx1z..."
  }
}
```

The launch policy is zero platform fee. If a later fee is introduced, the fee
address must be a dedicated public BTX Start address, not a personal payout
address.

## Required Backend Components

Minimum production backend:

- synced `btxd` mainnet node with RPC locked to localhost/private network
- stratum server compatible with the current `dexbtx-miner` client
- per-worker share database keyed by `(payout_address, worker_name)`
- PPLNS accounting and payout journal
- payout wallet with explicit operator approval flow
- public stats API
- per-wallet dashboard API
- monitoring for stale jobs, rejected shares, block propagation, RPC health,
  payout failures, and wallet balance

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
EXPECTED_POOL_FEE_BPS='0' \
EXPECTED_FEE_ADDRESS='btx1z...platform-fee...' \
EXPECTED_TREASURY_ADDRESS='btx1z...platform-treasury...' \
PROTECTED_PAYOUT_ADDRESSES='btx1z...personal...,btx1z...vast...' \
scripts/verify-owned-backend.sh
```

Only after that passes:

1. Change `DEFAULT_POOL` in `install.sh` to `stratum.drinknile.com:3333`.
2. Change the live stats source from `stats-snapshot.json` to
   `https://api.drinknile.com/stats`.
3. Set `platform-treasury.json` `owned_backend_active` and `active` to `true`.
4. Run installer preflight against the owned pool.
5. Run one miner with a new test payout address and verify shares appear in
   the first-party dashboard.

## Deployment Blocker In This Workspace

This machine currently has no `btxd`, no Docker/cloud deployment CLI for a VM,
no valid Vercel token, and no public pool backend source code. GitHub Pages can
host the website, but it cannot host a TCP stratum server or BTX wallet daemon.
