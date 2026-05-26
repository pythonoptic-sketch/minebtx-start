# BTX Wallet and Miner Setup

Use this guide for the BTX Start onboarding page.

## 1. Use your own BTX address

Generate or copy a personal BTX payout address that starts with `btx1z`.
Paste that address into the start form on the site. The command is generated in
your browser and is not sent to this static site.

## 2. Run preflight first

Preflight checks your host without installing packages or writing config:

```sh
curl -fsSL https://pythonoptic-sketch.github.io/minebtx-start/install.sh | bash -s -- --preflight --address 'btx1z...YOUR_BTX_ADDRESS...' --worker 'default'
```

It checks the operating system, required tools, NVIDIA GPU visibility, release
artifact reachability, stratum TCP reachability, and payout address format.

## 3. Run the hosted installer

The page generates a command like this:

```sh
curl -fsSL https://pythonoptic-sketch.github.io/minebtx-start/install.sh | bash -s -- --address 'btx1z...YOUR_BTX_ADDRESS...' --worker 'default'
```

Run it on a Linux machine with an NVIDIA GPU. The installer writes a miner
configuration under `~/.dexbtx-miner/` and starts from your payout address.

## 4. Track work and balances

The page gives you the matching Telegram lookup command:

```text
/mybalance btx1z...YOUR_BTX_ADDRESS.default
```

Balance lookup currently depends on the existing BTX Telegram bot. That is a
backend dependency, not infrastructure owned by this frontend.

You can visually follow the mining process today through three signals:

```sh
tail -f ~/.dexbtx-miner/miner.log
watch -n 2 nvidia-smi
```

The miner log should show accepted shares. `nvidia-smi` should show sustained
GPU utilization and power draw. Telegram can show balance and block-credit
lookups for the worker id generated on the page.

## 5. Current infrastructure status

BTX Start now owns the public onboarding page and installer entry URL. It does
not yet own an independent stratum pool, payout backend, stats API, Telegram
bot, or binary release pipeline.

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
step is to deploy our own stratum endpoint, stats API, payout wallet, bot, and
release artifacts, then point the installer at those services.
