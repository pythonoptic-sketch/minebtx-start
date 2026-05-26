# Hetzner CPX31 Setup

This is the cheapest sensible production path for the BTX Start managed mining
service. Users do not set up nodes; this server runs the service side.

## What to Create

Create one Hetzner Cloud server:

| Setting | Value |
|---|---|
| Location | US East/West if available, otherwise Germany or Finland |
| Image | Ubuntu 24.04 |
| Type | CPX31 |
| CPU/RAM | 4 vCPU / 8 GB RAM |
| Disk | 160 GB local NVMe |
| IPv4 | Enabled |
| Backups | Optional after launch; off for cheapest testing |
| SSH key | Add your local SSH public key |

Do not add an extra volume yet.

## Firewall

Allow inbound:

| Port | Protocol | Purpose |
|---|---|---|
| 22 | TCP | SSH administration |
| 443 | TCP | `api.drinknile.com` HTTPS API |
| 3333 | TCP | `stratum.drinknile.com` miner connections |
| 19335 | TCP | Optional BTX P2P inbound |

Allow outbound traffic.

## DNS

Keep the apex/root GitHub Pages records for `drinknile.com` as they are.

Add these custom records at the DNS provider:

| Type | Name | Value |
|---|---|---|
| A | `api` | Hetzner server IPv4 |
| A | `stratum` | Hetzner server IPv4 |

Wait until these resolve:

```bash
dig +short api.drinknile.com
dig +short stratum.drinknile.com
```

## First SSH Login

From your machine:

```bash
ssh root@<server-ip>
```

On the server:

```bash
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y git curl ca-certificates jq netcat-openbsd
git clone https://github.com/pythonoptic-sketch/minebtx-start.git /opt/btx-start
cd /opt/btx-start
deploy/scripts/server-readiness-check.sh
```

## Runtime Environment

Create a dedicated BTX Start fee/treasury address first. Do not use a personal
mining address.

Then run:

```bash
sudo FEE_ADDRESS='btx1z...BTX_START_FEE_ADDRESS...' \
  TREASURY_ADDRESS='btx1z...BTX_START_FEE_ADDRESS...' \
  deploy/scripts/generate-runtime-env.sh
```

This writes `/etc/btx-start/backend.env` with private RPC credentials.

## BTX Node

Build or provide a trusted `btxd` / `btx-cli` bundle. The deploy script expects a
tarball containing both binaries:

```bash
sudo BTX_NODE_TARBALL=/secure/path/btx-daemon.tar.gz \
  deploy/scripts/install-btx-node.sh
```

Wait until sync is complete:

```bash
sudo -u btx /usr/local/bin/btx-cli -conf=/etc/btx/btx.conf getblockchaininfo
```

Proceed only when `initialblockdownload` is `false`.

## Start API and Stratum Scaffold

```bash
sudo deploy/scripts/bootstrap-ubuntu.sh
```

Check:

```bash
curl -fsS http://127.0.0.1:8000/health
curl -fsS https://api.drinknile.com/health
nc -vz stratum.drinknile.com 3333
```

## Launch Gate

The current stratum service is a scaffold. It records workers and rejected share
submits, but it must not publicly accept shares until BTX MatMul share
validation and block submission are implemented.

Keep this production setting:

```text
ALLOW_UNVERIFIED_SHARE_ACCEPTANCE=false
```

After real share validation is implemented and one private test miner submits
accepted shares, run:

```bash
EXPECTED_FEE_ADDRESS='btx1z...BTX_START_FEE_ADDRESS...' \
EXPECTED_TREASURY_ADDRESS='btx1z...BTX_START_FEE_ADDRESS...' \
PROTECTED_PAYOUT_ADDRESSES='btx1z...YOUR_PERSONAL_ADDRESS...' \
deploy/scripts/activate-owned-backend.sh
```

Then commit and push the updated public JSON files.
