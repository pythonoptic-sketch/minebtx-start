# Windows Setup

This is the dedicated Windows path for desktops, laptops, and gaming PCs with
NVIDIA GPUs. Windows users run the miner inside Ubuntu on WSL2 so the installer
can use the same Linux/NVIDIA CUDA path as rented GPU hosts.

## 1. Install the Windows NVIDIA driver

Install the current NVIDIA driver from NVIDIA or GeForce Experience. Reboot
Windows after the driver install if prompted.

## 2. Install Ubuntu under WSL2

Open PowerShell and run:

```powershell
wsl --install -d Ubuntu
```

Restart Windows if prompted. After restart, open the Ubuntu app from the Start
menu and finish the Ubuntu username/password setup.

## 3. Confirm the GPU is visible inside Ubuntu

Run this inside the Ubuntu terminal:

```bash
nvidia-smi
```

If that command fails, fix the Windows NVIDIA driver or WSL2 install before
running the miner installer. The miner needs the GPU visible inside Ubuntu.

## 4. Preflight

Run this inside the Ubuntu terminal:

```bash
curl -fsSL https://drinknile.com/install.sh | bash -s -- \
  --preflight \
  --address 'btx1z...YOUR_BTX_ADDRESS...' \
  --worker 'windows'
```

Preflight checks:

- Ubuntu under WSL2
- NVIDIA GPU visibility through `nvidia-smi`
- payout address format
- TCP reachability to `stratum.drinknile.com:3333`
- installer dependencies needed for the Linux/NVIDIA path

## 5. Install

Run this inside the Ubuntu terminal after preflight passes:

```bash
curl -fsSL https://drinknile.com/install.sh | bash -s -- \
  --address 'btx1z...YOUR_BTX_ADDRESS...' \
  --worker 'windows'
```

The generated config uses your personal payout address and writes the miner
files under `~/.dexbtx-miner` inside Ubuntu.

## 6. Run and watch

Start the miner:

```bash
dexbtx-miner --config ~/.dexbtx-miner/config.yaml
```

Or run it persistently in `tmux`:

```bash
tmux new -d -s dexbtx 'dexbtx-miner --config ~/.dexbtx-miner/config.yaml 2>&1 | tee -a ~/.dexbtx-miner/miner.log'
tmux attach -t dexbtx
```

Watch for accepted shares:

```bash
tail -f ~/.dexbtx-miner/miner.log
```

## What this does not do

- It does not touch your personal BTX wallet or private keys.
- It does not custody mined BTX.
- It does not run from PowerShell; run the miner commands inside Ubuntu.
- It does not make non-NVIDIA Windows machines a practical mining target.
