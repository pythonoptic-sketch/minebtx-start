# BTX Start Platform Treasury

BTX Start should use a dedicated public fee wallet, not a personal day-to-day
wallet. The fee wallet is for platform revenue, infrastructure, security,
miner tooling, and collectively selected new BTX projects.

Treasury spending must be publicly explained. It does not create miner
ownership, dividends, or profit-sharing claims.

## Current Status

- Platform fee wallet: pending creation
- Target platform fee: `0.50%` / `50 bps`
- Active backend fee: still controlled by the current backend
- Active backend fee address: read from `stats-snapshot.json`
- Active backend pending fee: read from `pool.pending_fee_sat`

The static site cannot redirect fees. Fee routing changes only when the pool
backend is configured with the BTX Start fee address.

## Create the Dedicated Fee Wallet

Run this on the machine that will custody the BTX Start fee wallet and has
`btxd`/`btx-cli` configured:

```sh
scripts/create-platform-fee-wallet.sh
```

The script writes public metadata to `platform-treasury.local.json`. That file
is ignored by git. Copy only the public address fields into
`platform-treasury.json` when ready.

Never commit wallet files, seed material, exported keys, RPC cookies, or
private keys.

## Backend Policy to Deploy

After the public fee address is created, configure the pool backend:

```text
pool_fee_bps = 50
fee_address = "<BTX_START_PLATFORM_FEE_ADDRESS>"
treasury_address = "<BTX_START_PLATFORM_TREASURY_ADDRESS>"
```

The same placeholders are included in `backend/pool-policy.example.env`.

Then verify that the backend stats API reports the same values:

```sh
curl -s https://stats.minebtx.com/stats | jq '.policy'
```

Only after that verification should the website mark the platform treasury as
connected.
