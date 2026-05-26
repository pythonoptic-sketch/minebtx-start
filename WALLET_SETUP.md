# BTX Wallet and Miner Setup

Use this guide for the BTX Start onboarding page.

## 1. Use your own BTX address

Generate or copy a personal BTX payout address that starts with `btx1z`.
Paste that address into the start form on the site. The command is generated in
your browser and is not sent to this static site.

## 2. Run preflight first

Preflight checks your host without installing packages or writing config:

```sh
curl -fsSL https://drinknile.com/install.sh | bash -s -- --preflight --address 'btx1z...YOUR_BTX_ADDRESS...' --worker 'default'
```

It checks the operating system, required tools, NVIDIA GPU visibility, release
artifact reachability, stratum TCP reachability, and payout address format.

## 3. Run the hosted installer

The page generates a command like this:

```sh
curl -fsSL https://drinknile.com/install.sh | bash -s -- --address 'btx1z...YOUR_BTX_ADDRESS...' --worker 'default'
```

Run it on a Linux machine with an NVIDIA GPU. The installer writes a miner
configuration under `~/.dexbtx-miner/` and starts from your payout address.

## 4. Track work and balances

You can visually follow the mining process today through local miner signals
and the public network snapshot:

```sh
tail -f ~/.dexbtx-miner/miner.log
watch -n 2 nvidia-smi
```

The miner log should show accepted shares. `nvidia-smi` should show sustained
GPU utilization and power draw. The site shows the worker id, searchable GPU
profile estimates, expected BTX/hour, active workers, recent blocks, network
hashrate, and backend fee state.

Wallet balance should be checked in the BTX wallet that owns your payout
address until BTX Start ships a first-party per-wallet dashboard.

## 5. Current infrastructure status

BTX Start now owns the public onboarding page and installer entry URL. It does
not yet mark the backend as live, but the default miner target is already the
first-party stratum endpoint: `stratum.drinknile.com:3333`. This avoids moving
miners from an old pool later.

The first-party stats target is `https://api.drinknile.com/stats`. Until that
API is live, the site shows a provisioning snapshot with a 7-day free trial,
`post_trial_fee_bps = 50`, and zero active workers.

BTX Start should use a dedicated public platform treasury address for fees. The
target policy gives each payout address 7 days at 0.00%, then applies a 0.50%
fee through backend payout accounting. The platform fee is intended to fund
infrastructure, security, miner tooling, and collectively selected new BTX
projects. It should not be a personal day-to-day wallet, and it should not
imply miner ownership, dividends, or profit-sharing.

Before announcing the pool as live, deploy the stratum endpoint, stats API,
payout wallet, per-wallet dashboard, and release artifacts, then run
`scripts/verify-owned-backend.sh`. Your personal mining address must stay a
miner payout address only; never use it as the backend fee wallet, treasury
wallet, hot wallet, or payout aggregation wallet.
