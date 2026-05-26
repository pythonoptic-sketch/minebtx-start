# Production Backend Deployment

This is the guarded path to make `OWNED_BACKEND_ACTIVE=true`.

Current local status: this workstation does not have `btxd`, `btx-cli`, a
backend VM, or DNS provider credentials. The steps below must run on the
actual backend server and at the DNS provider.

## 1. Create a Backend Server

Use a Linux VM with:

- Ubuntu 22.04 or 24.04
- public IPv4
- 4+ vCPU
- 16+ GB RAM
- 1 TB SSD minimum for chainstate headroom
- inbound TCP 443 and 3333 open
- outbound peer connectivity for `btxd`; inbound TCP 19335 is recommended for a healthier public node
- SSH access

Set DNS once the server IP exists:

| Type | Name | Value |
|---|---|---|
| A | `api` | backend server IPv4 |
| A | `stratum` | backend server IPv4 |

Keep the root `drinknile.com` records pointed at GitHub Pages.

## 2. Create the Dedicated Fee Wallet

Do this on the backend custody machine after `btxd` and `btx-cli` exist:

```bash
scripts/create-platform-fee-wallet.sh
```

This writes `platform-treasury.local.json`. Do not commit private wallet data.
Only the public address can be copied into deployment env.

## 3. Generate Runtime Env

On the backend server:

```bash
sudo FEE_ADDRESS='btx1z...PLATFORM_FEE_ADDRESS...' \
  TREASURY_ADDRESS='btx1z...PLATFORM_FEE_ADDRESS...' \
  deploy/scripts/generate-runtime-env.sh
```

This writes `/etc/btx-start/backend.env` with random BTX RPC credentials.

## 4. Install BTX Node

The current GitHub release used by this site only publishes `btx-gbt-solve`.
It does not publish `btxd` or `btx-cli`. Provide a trusted daemon bundle:

```bash
sudo BTX_NODE_TARBALL=/secure/path/btx-daemon.tar.gz \
  deploy/scripts/install-btx-node.sh
```

Or with a verified URL:

```bash
sudo BTX_NODE_TARBALL_URL='https://trusted.example/btx-daemon.tar.gz' \
  BTX_NODE_TARBALL_SHA256='<sha256>' \
  deploy/scripts/install-btx-node.sh
```

Wait for sync:

```bash
sudo -u btx /usr/local/bin/btx-cli -conf=/etc/btx/btx.conf getblockchaininfo
```

Do not proceed while initial block download is true.

## 5. Bootstrap API and Stratum Services

```bash
sudo deploy/scripts/bootstrap-ubuntu.sh
```

Check:

```bash
curl -fsS http://127.0.0.1:8000/health
curl -fsS https://api.drinknile.com/health
nc -vz stratum.drinknile.com 3333
```

## 6. Keep Share Acceptance Disabled Until Validation Exists

`ALLOW_UNVERIFIED_SHARE_ACCEPTANCE=false` must remain false in production.

The scaffold can accept authorization and record rejected submits, but real
launch requires BTX matmul share validation and block submission connected to
the current job template.

## 7. Verify and Activate Public Status

After API, stratum, synced `btxd`, fee wallet, and share validation are live:

```bash
EXPECTED_FEE_ADDRESS='btx1z...PLATFORM_FEE_ADDRESS...' \
EXPECTED_TREASURY_ADDRESS='btx1z...PLATFORM_FEE_ADDRESS...' \
PROTECTED_PAYOUT_ADDRESSES='btx1z...PERSONAL...,btx1z...VAST...' \
deploy/scripts/activate-owned-backend.sh
```

This script refuses to update public JSON unless
`scripts/verify-owned-backend.sh` passes.

Review, commit, and push the resulting `platform-treasury.json` and
`stats-snapshot.json`.
