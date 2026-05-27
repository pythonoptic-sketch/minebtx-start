# BTX Start Backend

This folder contains the first-party backend scaffold for:

- `api.drinknile.com`
- `stratum.drinknile.com:3333`
- share accounting
- 7-day trial and post-trial platform fee ledger
- payout planning
- optional card-backed Pro membership

It does not include private keys, wallet files, RPC cookies, Stripe secrets, or
a synced BTX node.

## Services

### API

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements.txt
export $(grep -v '^#' backend/.env.example | xargs)
uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

Endpoints:

- `GET /health`
- `GET /stats`
- `GET /policy`
- `GET /dashboard/{payout_address}`
- `POST /billing/checkout`
- `POST /billing/webhook`

### Stratum

```bash
btxstart-stratum --port 3333
```

The stratum service handles JSON-RPC framing, subscribe, authorize, live
`mining.notify` job creation from `btxd getmatmulchallenge`, worker tracking,
and accepted/rejected share accounting.

Submitted shares are rejected unless either:

- `SHARE_VALIDATION_MODE=solver` points at a patched `btx-gbt-solve` binary
  that can reproduce the submitted nonce against the pool share target; or
- `ALLOW_UNVERIFIED_SHARE_ACCEPTANCE=true` is enabled for local development.

Do not enable unverified acceptance in production. Real production launch still
needs full-block construction and `submitblock` wiring before
`OWNED_BACKEND_ACTIVE=true`.

### Payout Worker

Dry run:

```bash
btxstart-payouts
```

Execute:

```bash
btxstart-payouts --execute
```

Execution calls `btx-cli` functionality through backend JSON-RPC. Only run it
on the locked backend machine after reviewing the dry-run output.

### Network Agent

```bash
btxstart-network-agent --once
```

The network agent watches the public BTX peer-list endpoint used by the peer
dashboard, reads local `btxd` health, writes a snapshot, and records a backend
event. It is observe-only by default. Keep `NETWORK_AGENT_APPLY_PEERS=false`
unless you explicitly want it to call `addnode` on the local node.

## Required Production Environment

Copy `backend/.env.example` to a private env file on the server and fill:

- `BTX_RPC_URL`
- `BTX_RPC_USER`
- `BTX_RPC_PASSWORD`
- `FEE_ADDRESS`
- `TREASURY_ADDRESS`
- optional Stripe values

Never commit the real env file.

## Launch Gates

Before setting `OWNED_BACKEND_ACTIVE=true`:

1. `btxd` is fully synced.
2. Dedicated fee/treasury address exists and is not a personal payout address.
3. `GET /health` reports node reachable and synced.
4. `GET /stats` reports the exact public policy.
5. Stratum accepts authorize and rejects invalid submits.
6. `SHARE_VALIDATION_MODE=solver` is active on the backend host.
7. Full-block construction and `submitblock` wiring are enabled.
8. One test miner can submit accepted shares to a test payout address.
9. Dashboard shows worker, shares, balance, fee state, and payout history.
10. `scripts/verify-owned-backend.sh` passes against production URLs.

## Billing Position

Base mining should remain address-only and no-card. Credit-card membership
should unlock optional Pro features only. See `../BILLING_MODEL.md`.
