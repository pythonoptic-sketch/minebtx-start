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

The stratum scaffold handles JSON-RPC framing, subscribe, authorize, worker
tracking, and rejected submit accounting. It intentionally rejects submitted
shares unless `ALLOW_UNVERIFIED_SHARE_ACCEPTANCE=true`.

Do not enable unverified acceptance in production. Real production launch still
needs BTX matmul share validation and block submission wiring.

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
6. Valid share verification is implemented.
7. One test miner can submit accepted shares to a test payout address.
8. Dashboard shows worker, shares, balance, fee state, and payout history.
9. `scripts/verify-owned-backend.sh` passes against production URLs.

## Billing Position

Base mining should remain address-only and no-card. Credit-card membership
should unlock optional Pro features only. See `../BILLING_MODEL.md`.
