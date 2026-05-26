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
not yet own an independent stratum pool, payout backend, stats API, per-wallet
dashboard, or binary release pipeline.

The current backend reports its fee policy through the stats snapshot. As of the
latest checked snapshot, `pool_fee_bps` is `250`, meaning 2.50%. That fee goes
to the backend-configured fee and treasury addresses, not to BTX Start unless
those backend addresses and policy are moved under BTX Start control.

BTX Start should use a dedicated public platform treasury address for fees. The
platform fee is intended to fund infrastructure, security, miner tooling, and
collectively selected new BTX projects. It should not be a personal day-to-day
wallet, and it should not imply miner ownership, dividends, or profit-sharing.

Until those are deployed, mining still depends on the existing BTX backend
configured by the installer. To become a fully independent competitor, the next
step is to deploy our own stratum endpoint, stats API, payout wallet,
per-wallet dashboard, and release artifacts, then point the installer at those
services.
