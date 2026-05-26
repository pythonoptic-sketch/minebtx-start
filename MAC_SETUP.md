# Apple Silicon Mac Setup

This is the dedicated Mac path for Apple Silicon machines, including
MacBook Pro, Mac mini, Mac Studio, Mac Pro, Max-class chips, and Ultra-class
chips.

The important constraint: the pinned public solver artifact is currently the
Linux/NVIDIA release. A Mac miner needs a patched Apple Silicon
`btx-gbt-solve` binary with all of these capabilities:

- `--share-target`
- `--daemon`
- `--backend metal` or `--backend mlx`

Until an official Mac release artifact is published and SHA256-pinned, the
installer requires `--local-solver` plus `--trust-local-solver` for Mac.
That is deliberate: we should not pretend the Linux CUDA binary is a verified
Mac binary.

## 1. Install Mac tools

```bash
xcode-select --install
brew install python coreutils tmux
python3 -m pip install --user --upgrade pyyaml
```

## 2. Put the Mac solver in the expected location

Copy or build the patched Apple Silicon solver, then place it here:

```bash
mkdir -p "$HOME/.dexbtx-miner/bin"
cp /path/to/macos/btx-gbt-solve "$HOME/.dexbtx-miner/bin/btx-gbt-solve"
chmod +x "$HOME/.dexbtx-miner/bin/btx-gbt-solve"
shasum -a 256 "$HOME/.dexbtx-miner/bin/btx-gbt-solve"
```

Keep that SHA256 value. The installer prints it again during install so the
operator can publish or compare it.

## 3. Preflight

```bash
curl -fsSL https://drinknile.com/install.sh | bash -s -- \
  --preflight \
  --solver-backend metal \
  --local-solver "$HOME/.dexbtx-miner/bin/btx-gbt-solve" \
  --trust-local-solver \
  --address 'btx1z...YOUR_BTX_ADDRESS...' \
  --worker 'mac-ultra'
```

Preflight checks:

- Apple Silicon macOS
- Metal or MLX backend selection
- local solver presence and executable bit
- local solver SHA256
- payout address format
- TCP reachability to `stratum.drinknile.com:3333`

## 4. Install

```bash
curl -fsSL https://drinknile.com/install.sh | bash -s -- \
  --address 'btx1z...YOUR_BTX_ADDRESS...' \
  --worker 'mac-ultra' \
  --solver-backend metal \
  --local-solver "$HOME/.dexbtx-miner/bin/btx-gbt-solve" \
  --trust-local-solver
```

The generated config uses your personal payout address and writes:

```yaml
solver_backend: "metal"
gbt_solve_path: "~/.dexbtx-miner/bin/btx-gbt-solve"
```

## 5. Mac starting profiles

These are starting points only. Run the benchmark on each machine.

| Mac class | CPU shape | Starting profile |
|---|---:|---|
| MacBook Air / base Mac mini | 8-10 CPU cores | workers=6, threads=4, batch=64, prefetch=4 |
| MacBook Pro Max / Mac Studio Max | 16-20 CPU cores | workers=12, threads=4, batch=64, prefetch=4 |
| Mac Studio Ultra / Mac Pro Ultra | 28+ CPU cores | workers=24, threads=8, batch=64, prefetch=4 |

The installer chooses these defaults by CPU count. The real source of truth is
the accepted-share rate the machine sustains.

## 6. Benchmark

```bash
dexbtx-miner benchmark \
  --backend metal \
  --threads 8 \
  --workers 6,12,24 \
  --batches 32,64,128 \
  --write-config
```

For Max-class machines, also test `--threads 4`. For Ultra-class machines,
test both `--threads 8` and `--threads 12` if the machine stays responsive.

## 7. Run and watch

```bash
tmux new -d -s dexbtx 'dexbtx-miner --config ~/.dexbtx-miner/config.yaml 2>&1 | tee -a ~/.dexbtx-miner/miner.log'
tmux attach -t dexbtx
```

Watch for accepted shares:

```bash
tail -f ~/.dexbtx-miner/miner.log
```

On macOS, Activity Monitor is the practical visual check for GPU and energy
pressure. If accepted shares do not appear, stop and inspect the solver output
before leaving the machine running.

## What this does not do

- It does not touch your personal BTX wallet or private keys.
- It does not custody mined BTX.
- It does not make CPU-only Intel Macs profitable.
- It does not prove Mac profitability against rented NVIDIA GPUs until real
  accepted-share data is collected from Mac miners.
