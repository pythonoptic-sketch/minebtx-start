# BTX Start Platform Treasury

BTX Start gives each payout address a 7-day 0.00% platform-fee trial. After
that trial, the target platform fee is 0.50%. BTX Start should use a dedicated
public fee wallet, not a personal day-to-day wallet. The fee wallet would fund
infrastructure, security, miner tooling, and collectively selected new BTX
projects.

Treasury spending must be publicly explained. It does not create miner
ownership, dividends, or profit-sharing claims.

## Current Status

- Platform fee wallet: pending creation
- Trial platform fee: `0.00%` / `0 bps` for 7 days per payout address
- Post-trial platform fee: `0.50%` / `50 bps`
- Owned backend: provisioning
- Active backend fee: pending first-party backend cutover
- Backend fee address: pending dedicated first-party wallet
- Backend pending fee: `0.00000000 BTX`

The static site cannot redirect fees by itself. Fee routing becomes real only
when the owned pool backend records each payout address's first accepted share,
applies the 7-day trial, deducts the fee through payout accounting after the
trial, and reports the same first-party fee address through
`https://api.drinknile.com/stats`.

Your personal mining address must stay a miner payout address only. It should
never be reused as the pool fee address, treasury address, hot wallet, or payout
aggregation wallet.

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
fee_model = "per_wallet_trial_then_pool_fee"
fee_routing = "pool_payout_accounting"
account_key_scope = "payout_address"
trial_days = 7
trial_fee_bps = 0
post_trial_fee_bps = 50
pool_fee_bps = 50
fee_address = "<BTX_START_PLATFORM_FEE_ADDRESS>"
treasury_address = "<BTX_START_PLATFORM_TREASURY_ADDRESS>"
```

The same placeholders are included in `backend/pool-policy.example.env`.

Then verify that the backend stats API reports the same values and that neither
backend address matches a protected personal payout address:

```sh
STATS_URL='https://api.drinknile.com/stats' \
STRATUM_HOST='stratum.drinknile.com' \
STRATUM_PORT='3333' \
EXPECTED_POOL_FEE_BPS='50' \
EXPECTED_TRIAL_DAYS='7' \
EXPECTED_TRIAL_FEE_BPS='0' \
EXPECTED_POST_TRIAL_FEE_BPS='50' \
PROTECTED_PAYOUT_ADDRESSES='btx1z...personal...' \
scripts/verify-owned-backend.sh
```

Only after that verification should the website mark the platform treasury as
connected.
