#!/usr/bin/env bash
# DEXBTX miner — one-line installer.
#
# Usage:
#   curl -fsSL https://drinknile.com/install.sh | bash
#   curl -fsSL https://drinknile.com/install.sh | bash -s -- --preflight
#   curl -fsSL https://drinknile.com/install.sh | bash -s -- --address btx1z...
#   curl -fsSL https://drinknile.com/install.sh | bash -s -- --solver-backend metal --local-solver ~/btx-gbt-solve --trust-local-solver --address btx1z...
#
# What this script does:
#   1. Detect OS + GPU (NVIDIA via nvidia-smi; Apple Silicon via Metal)
#   2. Install Python 3.10+ if missing
#   3. Install dexbtx-miner via pip
#   4. Download/copy the patched btx-gbt-solve binary, verify SHA256
#      against the pinned value when using an official artifact
#   5. Prompt for the user's btx1z... payout address (or accept --address)
#   6. Save config to ~/.dexbtx-miner/config.yaml
#   7. Print the launch command (and an optional systemd unit)
#
# This script is idempotent — re-running upgrades to the latest stable
# version. Existing config is preserved.

set -euo pipefail
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${PATH:-}"

# ─── Configurables ──────────────────────────────────────────────────────────
# Pin the release tag. install.sh always pulls this version of the solver
# binary as a release asset.
#
# The binary's SHA256 is the SINGLE SOURCE OF TRUTH in pyproject.toml under
# [tool.dexbtx-miner.solver].expected_sha256. install.sh fetches that file
# at install time and reads the hash from it (see fetch + parse block ~L170)
# rather than carrying its own duplicate of the value. This means bumping
# the binary requires editing exactly one place (pyproject.toml) instead of
# three (install.sh, pyproject.toml, release-tooling/SHA256SUMS).
#
# EXPECTED_SHA256 env var is supported as an override for offline / mirror
# / fork use; if set, it skips the remote pyproject.toml fetch.
#
PREBUILDS_TAG="${PREBUILDS_TAG:-v4.3-sm89-native}"
BTX_START_REPO_URL="${BTX_START_REPO_URL:-https://github.com/pythonoptic-sketch/minebtx-start}"
PREBUILDS_BASE="${PREBUILDS_BASE:-${BTX_START_REPO_URL}/releases/download/${PREBUILDS_TAG}}"
DEFAULT_SOLVER_URL="${PREBUILDS_BASE}/btx-gbt-solve"
SOLVER_URL="${SOLVER_URL:-$DEFAULT_SOLVER_URL}"
PYPROJECT_URL="${PYPROJECT_URL:-https://raw.githubusercontent.com/pythonoptic-sketch/minebtx-start/main/pyproject.toml}"

# Default pool — override with --pool flag or DEXBTX_POOL env var.
# Keep this first-party from launch so future miners do not need migration.
DEFAULT_POOL="${DEXBTX_POOL:-stratum.drinknile.com:3333}"

# Install paths.
INSTALL_DIR="${HOME}/.dexbtx-miner"
SOLVER_PATH="${INSTALL_DIR}/bin/btx-gbt-solve"
CONFIG_PATH="${INSTALL_DIR}/config.yaml"

# ─── Parse CLI ──────────────────────────────────────────────────────────────
ADDRESS=""
WORKER=""
POOL="${DEFAULT_POOL}"
ASSUME_YES=0
SKIP_PROMPT=0
LOCAL_SOLVER=""   # if set: copy from this local path instead of downloading
TRUST_LOCAL_SOLVER=0 # if 1: install LOCAL_SOLVER without comparing it to the Linux release hash
SKIP_PIP=0        # if 1: don't pip install dexbtx-miner (useful when running from a source checkout)
PREFLIGHT=0       # if 1: check host readiness without installing anything
SOLVER_BACKEND="" # cuda|metal|mlx|cpu. Default: cuda on Linux, metal on Apple Silicon.

while [[ $# -gt 0 ]]; do
    case "$1" in
        --address) ADDRESS="$2"; shift 2 ;;
        --worker)  WORKER="$2";  shift 2 ;;
        --pool)    POOL="$2";    shift 2 ;;
        --yes|-y)  ASSUME_YES=1; SKIP_PROMPT=1; shift ;;
        --skip-prompt) SKIP_PROMPT=1; shift ;;
        --local-solver) LOCAL_SOLVER="$2"; shift 2 ;;
        --trust-local-solver) TRUST_LOCAL_SOLVER=1; shift ;;
        --solver-backend) SOLVER_BACKEND="$2"; shift 2 ;;
        --mac) SOLVER_BACKEND="metal"; shift ;;
        --skip-pip)    SKIP_PIP=1; shift ;;
        --preflight)   PREFLIGHT=1; SKIP_PROMPT=1; shift ;;
        --help|-h)
            printf '%s\n' \
                "BTX Start miner installer" \
                "" \
                "Usage:" \
                "  curl -fsSL https://drinknile.com/install.sh | bash" \
                "  curl -fsSL https://drinknile.com/install.sh | bash -s -- --preflight" \
                "  curl -fsSL https://drinknile.com/install.sh | bash -s -- --address btx1z..." \
                "" \
                "Options:" \
                "  --preflight       Check host readiness without installing anything" \
                "  --address VALUE   BTX payout address" \
                "  --worker VALUE    Worker name for dashboard/balance lookup" \
                "  --pool HOST:PORT  Override stratum pool endpoint" \
                "  --solver-backend  Solver backend: cuda, metal, mlx, or cpu" \
                "  --mac             Shortcut for --solver-backend metal" \
                "  --yes, -y         Regenerate config without prompting" \
                "  --skip-prompt     Do not prompt for missing address" \
                "  --skip-pip        Skip Python package install" \
                "  --local-solver    Use a local btx-gbt-solve binary" \
                "  --trust-local-solver" \
                "                    Trust --local-solver hash. Required for local Mac builds until an official Mac artifact is pinned."
            exit 0
            ;;
        *) echo "unknown arg: $1"; exit 1 ;;
    esac
done

# ─── Helpers ────────────────────────────────────────────────────────────────
log()  { echo -e "\033[1;34m[install]\033[0m $*"; }
warn() { echo -e "\033[1;33m[warn]\033[0m $*" >&2; }
err()  { echo -e "\033[1;31m[error]\033[0m $*" >&2; exit 1; }

need() {
    command -v "$1" >/dev/null 2>&1 || err "missing required tool: $1"
}

sha256_file() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" | awk '{print $1}'
    else
        err "missing required tool: sha256sum or shasum"
    fi
}

confirm() {
    [[ "$ASSUME_YES" -eq 1 ]] && return 0
    read -rp "$1 [y/N] " ans
    [[ "$ans" =~ ^[Yy]$ ]]
}

run_preflight() {
    local failures=0
    local warnings=0
    local os_name
    local arch_name
    local backend_name
    os_name="$(uname -s 2>/dev/null || echo unknown)"
    arch_name="$(uname -m 2>/dev/null || echo unknown)"
    backend_name="${SOLVER_BACKEND}"
    if [[ -z "$backend_name" ]]; then
        if [[ "$os_name" == "Darwin" ]]; then
            backend_name="metal"
        else
            backend_name="cuda"
        fi
    fi

    log "BTX Start preflight — release ${PREBUILDS_TAG}"
    echo "  OS:       ${os_name}"
    echo "  Arch:     ${arch_name}"
    echo "  Backend:  ${backend_name}"
    echo "  Pool:     ${POOL}"
    if [[ -n "$LOCAL_SOLVER" ]]; then
        echo "  Solver:   ${LOCAL_SOLVER} (local)"
    else
        echo "  Solver:   ${SOLVER_URL}"
    fi
    echo

    case "$os_name" in
        Linux) log "OS check: Linux supported" ;;
        Darwin)
            if [[ "$arch_name" == "arm64" && ( "$backend_name" == "metal" || "$backend_name" == "mlx" ) ]]; then
                log "OS check: Apple Silicon macOS supported through the ${backend_name} backend"
            else
                warn "macOS mining requires Apple Silicon plus --solver-backend metal or mlx"
                failures=$((failures + 1))
            fi
            ;;
        *)
            warn "unsupported OS for the one-line miner path: ${os_name}"
            failures=$((failures + 1))
            ;;
    esac

    for tool in curl python3; do
        if command -v "$tool" >/dev/null 2>&1; then
            log "tool check: ${tool} found"
        else
            warn "tool check: ${tool} missing"
            failures=$((failures + 1))
        fi
    done

    if command -v sha256sum >/dev/null 2>&1 || command -v shasum >/dev/null 2>&1; then
        log "tool check: SHA256 tool found"
    else
        warn "tool check: sha256sum/shasum missing; install coreutils before mining"
        failures=$((failures + 1))
    fi

    if [[ "$backend_name" == "cuda" ]]; then
        if command -v nvidia-smi >/dev/null 2>&1; then
            local gpu_query
            gpu_query="$(nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader 2>/dev/null | head -1 || true)"
            if [[ -z "$gpu_query" ]]; then
                gpu_query="$(nvidia-smi --query-gpu=name,driver_version --format=csv,noheader 2>/dev/null | head -1 || true)"
            fi
            if [[ -n "$gpu_query" ]]; then
                log "GPU check: ${gpu_query}"
                case "$gpu_query" in
                    *"GTX 9"*|*"GTX 10"*) echo "  Release path: native sm_61 cubin" ;;
                    *"GTX 16"*|*"RTX 20"*|*"RTX 30"*|*"A100"*|*"A40"*|*"A4000"*|*"A5000"*|*"A6000"*) echo "  Release path: sm_61 PTX JIT to this architecture" ;;
                    *"RTX 40"*) echo "  Release path: native sm_89 cubin" ;;
                    *"H100"*|*"H200"*) echo "  Release path: native sm_90 cubin" ;;
                    *"RTX 50"*) echo "  Release path: native sm_120 cubin" ;;
                    *) echo "  Release path: unknown from name; installer smoke test is authoritative" ;;
                esac
            else
                warn "nvidia-smi is present but no GPU was returned"
                failures=$((failures + 1))
            fi
        else
            warn "nvidia-smi missing. Install NVIDIA drivers or choose --solver-backend metal on Apple Silicon."
            failures=$((failures + 1))
        fi
    elif [[ "$backend_name" == "metal" || "$backend_name" == "mlx" ]]; then
        if [[ "$os_name" == "Darwin" && "$arch_name" == "arm64" ]]; then
            log "GPU check: Apple Silicon unified GPU path (${backend_name})"
            if command -v system_profiler >/dev/null 2>&1; then
                system_profiler SPDisplaysDataType 2>/dev/null | awk -F: '/Chipset Model|Total Number of Cores|Metal Support/ {gsub(/^[ \t]+/, "", $2); print "  " $1 ":" $2}' | head -6 || true
            fi
        else
            warn "${backend_name} backend is only supported here for Apple Silicon macOS"
            failures=$((failures + 1))
        fi
    else
        warn "backend ${backend_name} is not a productive mining path; use cuda or metal"
        warnings=$((warnings + 1))
    fi

    if command -v curl >/dev/null 2>&1; then
        if [[ -n "$LOCAL_SOLVER" ]]; then
            if [[ -f "$LOCAL_SOLVER" && -x "$LOCAL_SOLVER" ]]; then
                log "artifact check: local solver exists and is executable"
                log "artifact check: local solver SHA256 $(sha256_file "$LOCAL_SOLVER")"
            elif [[ -f "$LOCAL_SOLVER" ]]; then
                warn "artifact check: local solver exists but is not executable; run chmod +x ${LOCAL_SOLVER}"
                failures=$((failures + 1))
            else
                warn "artifact check: local solver does not exist: ${LOCAL_SOLVER}"
                failures=$((failures + 1))
            fi
        elif [[ "$os_name" == "Darwin" ]]; then
            warn "artifact check: macOS requires --local-solver or a Mac-specific SOLVER_URL until an official Mac release artifact is pinned"
            failures=$((failures + 1))
        else
            if curl -fsIL --max-time 15 "$SOLVER_URL" >/dev/null 2>&1; then
                log "artifact check: solver release is reachable"
            else
                warn "artifact check: solver release is not reachable from this host"
                failures=$((failures + 1))
            fi
        fi

        if [[ -n "$LOCAL_SOLVER" && "$TRUST_LOCAL_SOLVER" -eq 1 ]]; then
            log "artifact check: local solver hash trust was explicitly requested"
        else
            if curl -fsIL --max-time 15 "$PYPROJECT_URL" >/dev/null 2>&1; then
                log "artifact check: SHA256 pin source is reachable"
            else
                warn "artifact check: SHA256 pin source is not reachable from this host"
                failures=$((failures + 1))
            fi
        fi
    fi

    if command -v python3 >/dev/null 2>&1; then
        if python3 - "$POOL" <<'PY'
import socket
import sys

pool = sys.argv[1]
host, port = pool.rsplit(":", 1) if ":" in pool else (pool, "3333")
try:
    with socket.create_connection((host, int(port)), timeout=5):
        pass
except Exception:
    sys.exit(1)
PY
        then
            log "network check: stratum TCP ${POOL} reachable"
        else
            warn "network check: stratum TCP ${POOL} is not reachable from this host"
            failures=$((failures + 1))
        fi
    fi

    if [[ -n "$ADDRESS" ]]; then
        if [[ "$ADDRESS" =~ ^btx1z[0-9a-zA-Z]{50,}$ ]]; then
            log "address check: payout address format looks valid"
        else
            warn "address check: payout address does not match the expected btx1z... format"
            warnings=$((warnings + 1))
        fi
    else
        warn "address check: no payout address supplied; pass --address before installing"
        warnings=$((warnings + 1))
    fi

    echo
    if [[ "$failures" -eq 0 ]]; then
        log "preflight complete: no install blockers found (${warnings} warning(s))."
        echo "Next:"
        echo "  curl -fsSL https://drinknile.com/install.sh | bash -s -- --address 'btx1z...YOUR_BTX_ADDRESS...' --worker '${WORKER:-default}'"
        return 0
    fi

    warn "preflight found ${failures} blocker(s) and ${warnings} warning(s). Fix blockers before installing."
    return 2
}

if [[ "$PREFLIGHT" -eq 1 ]]; then
    run_preflight
    exit $?
fi

# ─── Detection ──────────────────────────────────────────────────────────────
log "DEXBTX miner installer — release ${PREBUILDS_TAG}"

OS="$(uname -s)"
ARCH="$(uname -m 2>/dev/null || echo unknown)"
if [[ -z "$SOLVER_BACKEND" ]]; then
    if [[ "$OS" == "Darwin" ]]; then
        SOLVER_BACKEND="metal"
    else
        SOLVER_BACKEND="cuda"
    fi
fi
case "$OS" in
    Linux)
        if [[ "$SOLVER_BACKEND" == "metal" || "$SOLVER_BACKEND" == "mlx" ]]; then
            err "${SOLVER_BACKEND} backend is for Apple Silicon macOS. Use --solver-backend cuda on Linux."
        fi
        ;;
    Darwin)
        if [[ "$ARCH" != "arm64" ]]; then
            err "macOS mining path requires Apple Silicon. Intel Macs are only useful for docs and wallet setup."
        fi
        if [[ "$SOLVER_BACKEND" != "metal" && "$SOLVER_BACKEND" != "mlx" ]]; then
            err "macOS requires --solver-backend metal or --solver-backend mlx"
        fi
        if [[ -z "$LOCAL_SOLVER" && "$SOLVER_URL" == "$DEFAULT_SOLVER_URL" ]]; then
            err "macOS requires --local-solver /path/to/macos/btx-gbt-solve until an official Mac release artifact is pinned. See MAC_SETUP.md."
        fi
        ;;
    *)      err "unsupported OS: $OS" ;;
esac

# GPU detection
HAS_NVIDIA=0
GPU_NAME=""
if command -v nvidia-smi >/dev/null 2>&1; then
    if nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1 | grep -q "."; then
        HAS_NVIDIA=1
        GPU_NAME="$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)"
        log "detected NVIDIA GPU: ${GPU_NAME}"
    fi
fi
if [[ "$HAS_NVIDIA" -eq 0 && "$SOLVER_BACKEND" == "cuda" ]]; then
    warn "no NVIDIA GPU detected — solver will run on CPU only (much slower)"
elif [[ "$OS" == "Darwin" ]]; then
    if command -v system_profiler >/dev/null 2>&1; then
        GPU_NAME="$(system_profiler SPDisplaysDataType 2>/dev/null | awk -F: '/Chipset Model/ {gsub(/^[ \t]+/, "", $2); print $2; exit}' || true)"
    fi
    GPU_NAME="${GPU_NAME:-Apple Silicon unified GPU}"
    log "detected Apple Silicon GPU path: ${GPU_NAME} (${SOLVER_BACKEND})"
fi

# Python
need curl
if ! command -v sha256sum >/dev/null 2>&1 && ! command -v shasum >/dev/null 2>&1; then
    err "missing required tool: sha256sum or shasum"
fi

PYTHON=""
for cand in python3.11 python3.10 python3; do
    if command -v "$cand" >/dev/null 2>&1; then
        PYTHON="$cand"
        if "$cand" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)'; then
            break
        fi
        PYTHON=""
    fi
done

if [[ -z "$PYTHON" ]]; then
    log "installing python3.11 via apt..."
    if command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update -qq
        sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3.11 python3.11-venv python3-pip
        PYTHON=python3.11
    else
        err "no python3.10+ found and apt-get not available — install Python 3.10+ manually then re-run"
    fi
fi
log "using Python: $($PYTHON --version 2>&1)"

log "checking first-party stratum reachability: ${POOL}"
if ! "$PYTHON" - "$POOL" <<'PY'
import socket
import sys

pool = sys.argv[1]
host, port = pool.rsplit(":", 1) if ":" in pool else (pool, "3333")
try:
    with socket.create_connection((host, int(port)), timeout=5):
        pass
except Exception:
    sys.exit(1)
PY
then
    err "stratum pool ${POOL} is not reachable yet. The BTX Start backend is still provisioning; run --preflight again before installing."
fi

# ─── Install pip + runtime deps + dexbtx-miner ──────────────────────────────
# Many vast.ai CUDA images ship without pip — install it via apt if missing.
if ! "$PYTHON" -m pip --version >/dev/null 2>&1; then
    log "python pip not present; installing via apt..."
    if command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update -qq
        sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3-pip
    else
        err "python pip missing and apt-get not available; install pip manually then re-run"
    fi
fi

# Runtime deps (pyyaml for --config). Install regardless of --skip-pip
# because --skip-pip only skips the dexbtx-miner package itself (useful for
# source-tree dev), not its transitive deps.
log "installing runtime deps (pyyaml)..."
"$PYTHON" -m pip install --user --quiet --upgrade pyyaml

if [[ "$SKIP_PIP" -eq 1 ]]; then
    log "skipping dexbtx-miner pip install (--skip-pip); assuming source tree is on PYTHONPATH"
else
    # Install the Python package directly from the GitHub source tarball
    # at the same release tag as the binary. This avoids needing a
    # git binary on the host AND avoids PyPI as a single point of
    # failure. Override DEXBTX_MINER_PKG_URL to install from a fork
    # / local checkout / private mirror.
    DEXBTX_MINER_PKG_URL="${DEXBTX_MINER_PKG_URL:-${BTX_START_REPO_URL}/archive/refs/heads/main.tar.gz}"
    log "installing dexbtx-miner from ${DEXBTX_MINER_PKG_URL} (pip --user)..."
    "$PYTHON" -m pip install --user --upgrade "$DEXBTX_MINER_PKG_URL"

    # Make sure ~/.local/bin is on PATH for the next session
    case ":$PATH:" in
        *":$HOME/.local/bin:"*) : ;;
        *) warn "add to your shell rc: export PATH=\"\$HOME/.local/bin:\$PATH\"" ;;
    esac
fi

# ─── Resolve EXPECTED_SHA256 from pyproject.toml (single source of truth) ─
# Unless the user passed EXPECTED_SHA256 via env var (offline / fork use),
# fetch the pyproject.toml from the release tag and extract the pinned hash.
# This keeps install.sh + pyproject.toml + SHA256SUMS from drifting.
if [[ -z "${EXPECTED_SHA256:-}" && ! ( -n "$LOCAL_SOLVER" && "$TRUST_LOCAL_SOLVER" -eq 1 ) ]]; then
    log "fetching solver SHA256 pin from ${PYPROJECT_URL}..."
    PYPROJECT_TMP="$(mktemp)"
    if ! curl -fsSL "$PYPROJECT_URL" -o "$PYPROJECT_TMP"; then
        rm -f "$PYPROJECT_TMP"
        err "could not fetch pyproject.toml from ${PYPROJECT_URL}. Pass EXPECTED_SHA256=<hash> to override."
    fi
    EXPECTED_SHA256="$(grep -E '^\s*expected_sha256\s*=' "$PYPROJECT_TMP" | head -1 | sed -E 's/.*"([a-f0-9]+)".*/\1/')"
    rm -f "$PYPROJECT_TMP"
    if [[ ! "$EXPECTED_SHA256" =~ ^[a-f0-9]{64}$ ]]; then
        err "could not extract a 64-char SHA256 from pyproject.toml; got: ${EXPECTED_SHA256:-<empty>}"
    fi
    log "pinned solver SHA256 (from pyproject.toml): $EXPECTED_SHA256"
fi
if [[ -n "$LOCAL_SOLVER" && "$TRUST_LOCAL_SOLVER" -eq 1 ]]; then
    warn "local solver trust mode enabled; install.sh will print the SHA256 but cannot compare this binary to the pinned Linux release hash."
fi

# ─── Fetch + verify solver ──────────────────────────────────────────────────
mkdir -p "${INSTALL_DIR}/bin"
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

if [[ -n "$LOCAL_SOLVER" ]]; then
    log "using local solver at ${LOCAL_SOLVER} (skipping download)"
    cp "$LOCAL_SOLVER" "$TMP"
else
    log "downloading patched btx-gbt-solve from ${SOLVER_URL}..."
    curl -fsSL "$SOLVER_URL" -o "$TMP"
fi

ACTUAL_SHA="$(sha256_file "$TMP")"
if [[ -n "$LOCAL_SOLVER" && "$TRUST_LOCAL_SOLVER" -eq 1 ]]; then
    log "local solver SHA256: ${ACTUAL_SHA}"
elif [[ "$ACTUAL_SHA" != "$EXPECTED_SHA256" ]]; then
    err "solver SHA256 mismatch — expected $EXPECTED_SHA256, got $ACTUAL_SHA. Aborting (refusing to install untrusted binary)."
else
    log "solver SHA256 verified ($EXPECTED_SHA256)"
fi

install -m 0755 "$TMP" "$SOLVER_PATH"
log "solver installed → $SOLVER_PATH"

# Smoke-test the binary. NOTE: btx-gbt-solve --help exits with code 1 (the
# upstream convention), so with `set -o pipefail` enabled we can't use
# `if ! cmd | grep` directly — capture the output first, grep separately.
HELP_OUT="$("$SOLVER_PATH" --help 2>&1 || true)"
if echo "$HELP_OUT" | grep -q "share-target"; then
    log "smoke-test: --share-target flag present ✓"
else
    err "installed solver lacks --share-target flag (the patch this release needs). Aborting."
fi
if echo "$HELP_OUT" | grep -q "daemon"; then
    log "smoke-test: --daemon flag present ✓"
else
    err "installed solver lacks --daemon flag — the dexbtx-miner wrapper runs the solver in daemon mode for persistent CUDA context. Aborting."
fi

# ─── Config ─────────────────────────────────────────────────────────────────
if [[ -z "$ADDRESS" && "$SKIP_PROMPT" -eq 0 ]]; then
    echo
    echo "Enter your BTX payout address (format: btx1z...):"
    read -rp "  address: " ADDRESS
fi

if [[ -n "$ADDRESS" ]]; then
    if [[ ! "$ADDRESS" =~ ^btx1z[0-9a-zA-Z]{50,}$ ]]; then
        warn "address does not match expected btx1z... format — proceeding anyway, but double-check"
    fi
fi

if [[ -z "$WORKER" ]]; then
    WORKER="$(hostname -s 2>/dev/null || echo default)"
fi

# Write config (preserve existing fields if file exists)
if [[ -f "$CONFIG_PATH" ]]; then
    log "config exists at $CONFIG_PATH — preserving (override with --yes to regenerate)"
    if [[ "$ASSUME_YES" -eq 1 ]]; then
        cp "$CONFIG_PATH" "${CONFIG_PATH}.bak.$(date +%s)"
        log "backed up old config"
    fi
fi

if [[ ! -f "$CONFIG_PATH" || "$ASSUME_YES" -eq 1 ]]; then
    # ───────────────────────────────────────────────────────────────────
    # Per-GPU tuning profile.
    #
    # THE MOST IMPORTANT LEVERS are PREPARE_WORKERS and SOLVER_THREADS —
    # the matmul backend is CPU-input-prep-bound on the faster Blackwell
    # cards. On an RTX 5070 we measured 70.6% util with workers=8 / threads=4
    # and 100% util with workers=16 / threads=8 (sweep 2026-05-25 on contract
    # 37712744). Batch size has zero effect once prep is sufficient.
    #
    # CPU sizing note: workers+threads should sum to ≤ effective vCPU count
    # of your container. The pool's solver is async (PIPELINE_ASYNC=1), so
    # idle workers don't burn cycles — over-provisioning is cheap.
    #
    # Profiles below are starting points calibrated against measured cards.
    # Run `dexbtx-miner benchmark` (TUNING.md) to dial in further.
    # ───────────────────────────────────────────────────────────────────
    GPU_BATCH=128
    GPU_PREFETCH=8
    GPU_WORKERS=8
    GPU_THREADS=4
    if [[ "$SOLVER_BACKEND" == "metal" || "$SOLVER_BACKEND" == "mlx" ]]; then
        CPU_COUNT="$(getconf _NPROCESSORS_ONLN 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 8)"
        GPU_BATCH=64
        GPU_PREFETCH=4
        GPU_WORKERS=6
        GPU_THREADS=4
        if [[ "$CPU_COUNT" -ge 28 ]]; then
            # Mac Studio / Mac Pro Ultra-class machines. Keep
            # workers+threads <= observed CPU count so developer machines
            # remain responsive while benchmarking.
            GPU_WORKERS=24
            GPU_THREADS=8
        elif [[ "$CPU_COUNT" -ge 16 ]]; then
            # Max-class Apple Silicon machines.
            GPU_WORKERS=12
            GPU_THREADS=4
        fi
    elif [[ "$GPU_NAME" == *"GTX 10"* || "$GPU_NAME" == *"GTX 9"* ]]; then
        # Pascal sm_61 (e.g. GTX 1070): memory-bound. Measured ceiling
        # ~83% util / 113W (75% of 150W TDP) at 16/8/128 — same ceiling
        # as the older 4/4/32 profile in practice; Pascal is bandwidth-
        # constrained regardless of input-prep rate. Standardized on the
        # universal modern profile for tuning consistency across gens.
        GPU_BATCH=128
        GPU_PREFETCH=8
        GPU_WORKERS=16
        GPU_THREADS=8
    elif [[ "$GPU_NAME" == *"RTX 2080 Ti"* || "$GPU_NAME" == *"RTX 20"* || "$GPU_NAME" == *"GTX 16"* ]]; then
        # Turing sm_75 (RTX 20-series, GTX 16-series). Measured: 12/8/128
        # → 100% util / 296W sustained on a boost-enabled host. Runs the
        # Pascal sm_61 PTX → JIT to sm_75 (no native sm_75 cubin).
        GPU_BATCH=128
        GPU_PREFETCH=8
        GPU_WORKERS=12
        GPU_THREADS=8
    elif [[ "$GPU_NAME" == *"RTX 30"* || "$GPU_NAME" == *"A100"* || "$GPU_NAME" == *"A40"* || "$GPU_NAME" == *"A4000"* || "$GPU_NAME" == *"A5000"* || "$GPU_NAME" == *"A6000"* ]]; then
        # Ampere — consumer 30-series (sm_86) + workstation/datacenter
        # A100 / A40 / Axxxx (sm_80). Measured on 3060 Ti: 12/8/128
        # → 100% util / 190W sustained (95% of 200W TDP). Runs the
        # Pascal sm_61 PTX → JIT (no native sm_80/sm_86 cubin in v4.3).
        GPU_BATCH=128
        GPU_PREFETCH=8
        GPU_WORKERS=12
        GPU_THREADS=8
    elif [[ "$GPU_NAME" == *"RTX 4060 Ti"* ]]; then
        # Ada Lovelace sm_89, 16GB. Measured: 12/8/128 → 100% util / 164W
        # sustained. Sweep tested batch=64/128/256; batch had zero effect
        # on steady-state util. The native sm_89 cubin requires v4.3+
        # (or sm_61 PTX → JIT fallback on v4.0-v4.2). Check with
        # `cuobjdump --list-elf` to confirm sm_89 is present.
        GPU_BATCH=128
        GPU_PREFETCH=8
        GPU_WORKERS=12
        GPU_THREADS=8
    elif [[ "$GPU_NAME" == *"RTX 4070"* || "$GPU_NAME" == *"RTX 4080"* || "$GPU_NAME" == *"RTX 4090"* ]]; then
        # Ada Lovelace sm_89, larger dies. Untested at this scale —
        # start from the 5070 profile (workers=16) and tune up.
        GPU_BATCH=128
        GPU_PREFETCH=8
        GPU_WORKERS=16
        GPU_THREADS=8
    elif [[ "$GPU_NAME" == *"RTX 5060 Ti"* ]]; then
        # Blackwell sm_120, 16GB. Measured: 16/8/128 → 99% util / 150W.
        # Standardized on the universal modern profile for consistency
        # with 5070 / 5070 Ti / 4060 Ti / 2080 Ti — over-provisioning
        # workers is cheap (async; idle workers don't burn cycles).
        GPU_BATCH=128
        GPU_PREFETCH=8
        GPU_WORKERS=16
        GPU_THREADS=8
    elif [[ "$GPU_NAME" == *"RTX 5070 Ti"* ]]; then
        # Blackwell sm_120, 16GB. NOTE: batch=256+prefetch=16 broke CUDA
        # on this card historically. Keep batch=128. Workers bumped for
        # the extra SM count vs 5060 Ti.
        GPU_BATCH=128
        GPU_PREFETCH=8
        GPU_WORKERS=16
        GPU_THREADS=8
    elif [[ "$GPU_NAME" == *"RTX 5070"* ]]; then
        # Blackwell sm_120, 12GB. Measured: 16/8/128 → 99.9% util / 223W
        # sustained. The 5060 Ti's workers=8 default caps the 5070 at
        # only 70.6% util — the extra SMs and higher boost clock starve
        # the prep pipeline. Bump to workers=16.
        GPU_BATCH=128
        GPU_PREFETCH=8
        GPU_WORKERS=16
        GPU_THREADS=8
    elif [[ "$GPU_NAME" == *"RTX 5080"* || "$GPU_NAME" == *"RTX 5090"* ]]; then
        # Blackwell sm_120 large-die. Untested at this scale — start from
        # the 5070 profile and tune up.
        GPU_BATCH=128
        GPU_PREFETCH=8
        GPU_WORKERS=16
        GPU_THREADS=8
    fi
    cat > "$CONFIG_PATH" <<YAML
# DEXBTX miner config — generated by install.sh
# Production-canonical solver tuning: env vars match upstream BTX matmul
# source names verified via grep getenv. Wrong names silently no-op
# (we shipped BTX_MATMUL_PREFETCH for a while; it doesn't exist).
#
# >>> THE TWO LEVERS THAT MATTER: solver_prepare_workers + solver_threads <<<
# These control CPU-side input generation for the matmul kernel. A
# Blackwell-class GPU at the canonical 5060 Ti tuning (workers=8) is
# CPU-input-bound at 70% util on cards faster than a 5060 Ti. Bump them
# to 16/8 if you have ≥16 effective vCPUs and the card is sub-100% util.
# Batch size, prefetch depth, and async flag do NOT meaningfully change
# steady-state throughput once prep is sufficient (verified by sweep).
pool_host: "${POOL%:*}"
pool_port: ${POOL##*:}
pool_tls: false

payout_address: "${ADDRESS}"
worker_name: "${WORKER}"

gbt_solve_path: "${SOLVER_PATH}"

# Solver tuning (per-GPU profile chosen from detected hardware: ${GPU_NAME:-CPU only})
solver_backend: "${SOLVER_BACKEND}"
solver_prepare_workers: ${GPU_WORKERS} # BTX_MATMUL_PREPARE_WORKERS (KEY LEVER — bump together with threads)
solver_threads: ${GPU_THREADS}         # BTX_MATMUL_SOLVER_THREADS  (KEY LEVER — bump together with workers)
solver_batch_size: ${GPU_BATCH}        # BTX_MATMUL_SOLVE_BATCH_SIZE
solver_prefetch_depth: ${GPU_PREFETCH} # BTX_MATMUL_PREPARE_PREFETCH_DEPTH
solver_pipeline_async: 1               # BTX_MATMUL_PIPELINE_ASYNC (overlap prep+kernel)
gpu_inputs: 0                          # BTX_MATMUL_GPU_INPUTS (CPU-gen inputs; the "GPU saturation breakthrough" fix)

nonces_per_slice: 20000000
reconnect_initial_s: 1.0
reconnect_max_s: 60.0

log_level: "INFO"
YAML
    log "config written → $CONFIG_PATH"
    log "  GPU profile:        workers=${GPU_WORKERS}  threads=${GPU_THREADS}  batch=${GPU_BATCH}  prefetch=${GPU_PREFETCH}"
    log "  if util stays below 95% during steady-state mining, bump workers + threads"
    log "  (workers and threads are the dominant levers on Blackwell)"
fi

# ─── Hard GPU acceleration smoke test ───────────────────────────────────────
# Runs the solver with --backend cuda against a deterministic input AND
# verifies CUDA actually engaged via three independent signals — solver
# alone reports JSON in CPU-fallback mode too, which is the silent-failure
# mode where a miner runs at ~6 N/s on CPU for hours without noticing.
#
# Three-assertion check (any failure aborts install):
#   (a) solver PID visible in nvidia-smi --query-compute-apps during run
#   (b) sustained GPU power > 100W (5060 Ti idle ~30W; engaged 150-180W)
#   (c) effective throughput > 1000 N/s — this uses tries_used/elapsed_s
#       which docs/TUNING.md correctly calls a misleading per-card rate
#       metric. Here it's used ONLY as a LIVENESS FLOOR (proves the
#       kernel did productive work, vs the CPU-fallback ~6 N/s case),
#       NOT as a tuning measurement. 1000 N/s is well below any real
#       GPU's actual rate (5060 Ti is 28000+) — failure means CPU
#       fallback or catastrophic kernel-launch failure, not a tuning
#       problem.
#
# If (a) fails, the binary lacks a kernel image compatible with this
# driver/GPU. The fix is ALWAYS to ship a binary that supports the user's
# driver — never to ask the user to downgrade. We aim at current drivers.
if [[ "$HAS_NVIDIA" -eq 1 ]]; then
    log "running GPU acceleration smoke test (20s with engagement assertions)..."

    # Background nvidia-smi poll for power curve
    POLL_OUT="$(mktemp)"
    APPS_OUT="$(mktemp)"
    trap 'rm -f "$POLL_OUT" "$APPS_OUT"' EXIT
    ( for i in $(seq 1 22); do
        nvidia-smi --query-gpu=utilization.gpu,power.draw --format=csv,noheader
        nvidia-smi --query-compute-apps=pid,process_name --format=csv,noheader >> "$APPS_OUT" 2>/dev/null
        sleep 1
      done ) > "$POLL_OUT" 2>&1 &
    POLL_PID=$!

    # CRITICAL: the smoke test must mirror the env-var setup the production
    # miner uses — most importantly BTX_MATMUL_GPU_INPUTS=0. Without it the
    # solver defaults to GPU-side input gen on most modern cards (the
    # "8% util / 33W silent fallback" path), which would correctly fail
    # assertion (b) but for the wrong reason — making install.sh look like
    # a host-power problem when the real issue is the smoke test exercising
    # a different code path than the production miner.
    SMOKE_OUT="$(BTX_MATMUL_BACKEND=cuda \
        BTX_MATMUL_GPU_INPUTS=0 \
        BTX_MATMUL_SOLVE_BATCH_SIZE=128 \
        BTX_MATMUL_PREPARE_PREFETCH_DEPTH=8 \
        BTX_MATMUL_PREPARE_WORKERS=8 \
        BTX_MATMUL_PIPELINE_ASYNC=1 \
        "$SOLVER_PATH" \
        --version 536870912 \
        --prev-hash 0ab38fdff2ef667dcddac7f50c3696080c26697615f7b6b9af5c3a1ba0a5fb7e \
        --merkle-root d906f02ed11d8936770423263b56c5ffe1ea1b15c8a2867afb161adb6fd76eb7 \
        --time 1779672814 --bits 0x1d17c609 \
        --share-target 00005f59c4000000000000000000000000000000000000000000000000000000 \
        --seed-a 8460daf3ff446cc55a7115de88ee24c8a2bf182eedde43abb9cf4cc94cc209bf \
        --seed-b 7f2e377616feb92d2e9857cab390595b7d6b8d24373a2da394f8d97197b5f437 \
        --block-height 110806 --nonce-start 1 \
        --max-tries 100000000 --max-seconds 20 \
        --backend cuda --solver-threads 4 --batch-size 128 2>&1 || true)"

    wait $POLL_PID 2>/dev/null || true

    SMOKE_LAST_LINE="$(echo "$SMOKE_OUT" | grep -E '^\{.*\}$' | tail -1)"
    if [[ -z "$SMOKE_LAST_LINE" ]]; then
        echo "$SMOKE_OUT" | tail -10 >&2
        err "GPU smoke test: solver produced no JSON output. CUDA backend likely failed to initialize. Aborting."
    fi

    # ASSERTION (a): solver appeared in compute-apps
    if ! grep -q btx-gbt-solve "$APPS_OUT" 2>/dev/null; then
        echo
        err "GPU smoke test FAILED (assertion a: nvidia-smi --query-compute-apps never saw btx-gbt-solve).

The solver silently fell back to CPU. The binary does NOT have a kernel image
compatible with your GPU/driver combination. Driver: $(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -1).

This is a binary issue, NOT a driver issue — DO NOT downgrade your driver.

Action: file an issue at github.com/pythonoptic-sketch/minebtx-start/issues with:
  - GPU model: ${GPU_NAME}
  - Driver version: $(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -1)
  - CUDA runtime: $(nvidia-smi --query-gpu=cuda_version --format=csv,noheader 2>/dev/null | head -1)

We will ship a binary build that supports your hardware. Until then this
install cannot proceed — running on CPU would burn money for trivial output."
    fi

    # ASSERTION (b): sustained power > 100W (need ≥10 samples above)
    HIGH_POWER_SAMPLES="$(awk -F, '{gsub(/[ W]/,"",$2); if ($2+0 > 100) c++} END{print c+0}' "$POLL_OUT")"
    if [[ "$HIGH_POWER_SAMPLES" -lt 10 ]]; then
        warn "GPU smoke test WARN (assertion b: only ${HIGH_POWER_SAMPLES}/20 samples above 100W)"
        warn "  Power curve was:"
        head -5 "$POLL_OUT" | sed 's/^/    /' >&2
        warn "  GPU compute engaged but at low power — host may be power-capping"
        warn "  or sharing physical GPU with another tenant. Throughput will be degraded."
    fi

    # ASSERTION (c): effective throughput > 1000 N/s
    THROUGHPUT_N_S="$(echo "$SMOKE_LAST_LINE" | python3 -c "
import sys, json
try:
    r = json.loads(sys.stdin.read())
    tries = r.get('tries_used', 0)
    elap = max(r.get('elapsed_s', 1), 0.01)
    print(int(tries / elap))
except Exception:
    print(0)
")"
    if [[ "$THROUGHPUT_N_S" -lt 1000 ]]; then
        err "GPU smoke test FAILED (assertion c: throughput ${THROUGHPUT_N_S} N/s, expected >1000).

Solver appeared in compute-apps and drew power, but effective throughput is
${THROUGHPUT_N_S} nonces/sec — far below the 1000 N/s floor that proves
the kernel ran productively. Canonical 5060 Ti is 28000+ N/s.

Possible causes:
  - Noisy neighbor sharing SMs on the same physical GPU
  - Thermal throttling under sustained load
  - Driver issue causing kernel launches to fail silently after first launch

This install cannot proceed at this throughput."
    fi

    log "GPU smoke test PASS:"
    log "  compute-app PID visible in nvidia-smi: yes"
    log "  sustained power: ${HIGH_POWER_SAMPLES}/20 samples >100W"
    log "  throughput: ${THROUGHPUT_N_S} N/s"
fi

if [[ "$OS" == "Darwin" && ( "$SOLVER_BACKEND" == "metal" || "$SOLVER_BACKEND" == "mlx" ) ]]; then
    log "running Apple Silicon ${SOLVER_BACKEND} solver smoke test (functional JSON check)..."
    MAC_SMOKE_OUT="$(BTX_MATMUL_BACKEND="$SOLVER_BACKEND" \
        BTX_MATMUL_GPU_INPUTS=0 \
        BTX_MATMUL_SOLVE_BATCH_SIZE="${GPU_BATCH:-64}" \
        BTX_MATMUL_PREPARE_PREFETCH_DEPTH="${GPU_PREFETCH:-4}" \
        BTX_MATMUL_PREPARE_WORKERS="${GPU_WORKERS:-6}" \
        BTX_MATMUL_PIPELINE_ASYNC=1 \
        "$SOLVER_PATH" \
        --version 536870912 \
        --prev-hash 0ab38fdff2ef667dcddac7f50c3696080c26697615f7b6b9af5c3a1ba0a5fb7e \
        --merkle-root d906f02ed11d8936770423263b56c5ffe1ea1b15c8a2867afb161adb6fd76eb7 \
        --time 1779672814 --bits 0x1d17c609 \
        --share-target 00ffffff00000000000000000000000000000000000000000000000000000000 \
        --seed-a 8460daf3ff446cc55a7115de88ee24c8a2bf182eedde43abb9cf4cc94cc209bf \
        --seed-b 7f2e377616feb92d2e9857cab390595b7d6b8d24373a2da394f8d97197b5f437 \
        --block-height 110806 \
        --matmul-n 512 --matmul-b 16 --matmul-r 8 --epsilon-bits 18 \
        --nonce-start 1 \
        --max-tries 100000000 --max-seconds 8 \
        --backend "$SOLVER_BACKEND" --solver-threads "${GPU_THREADS:-4}" --batch-size "${GPU_BATCH:-64}" 2>&1 || true)"
    MAC_SMOKE_LAST_LINE="$(echo "$MAC_SMOKE_OUT" | grep -E '^\{.*\}$' | tail -1)"
    if [[ -z "$MAC_SMOKE_LAST_LINE" ]]; then
        echo "$MAC_SMOKE_OUT" | tail -12 >&2
        err "Apple Silicon solver smoke test produced no JSON output. Check that your local btx-gbt-solve binary supports --backend ${SOLVER_BACKEND}."
    fi
    log "Apple Silicon solver smoke test PASS:"
    log "  backend: ${SOLVER_BACKEND}"
    log "  response: ${MAC_SMOKE_LAST_LINE}"
fi

# ─── Summary ────────────────────────────────────────────────────────────────
echo
log "✓ DEXBTX miner installed."
echo
echo "  Pool:     ${POOL}"
echo "  Address:  ${ADDRESS:-<edit ${CONFIG_PATH} and set payout_address>}"
echo "  Worker:   ${WORKER}"
echo "  GPU:      ${GPU_NAME:-CPU only}"
echo "  Backend:  ${SOLVER_BACKEND}"
echo
echo "Launch the miner:"
echo "  dexbtx-miner --config ${CONFIG_PATH}"
echo
echo "Or, for a long-running daemon (recommended):"
echo "  tmux new -d -s dexbtx 'dexbtx-miner --config ${CONFIG_PATH} 2>&1 | tee -a ${INSTALL_DIR}/miner.log'"
echo "  tmux attach -t dexbtx"
echo
echo "Stats + payouts: https://drinknile.com/#dashboard"
echo
echo "Tune for your specific GPU (the defaults are a starting point — every"
echo "card has a different sweet spot):"
if [[ "$OS" == "Darwin" ]]; then
    echo "  dexbtx-miner benchmark --backend ${SOLVER_BACKEND} --threads ${GPU_THREADS:-4} --workers 6,12,24 --batches 32,64,128"
    echo "  dexbtx-miner benchmark --backend ${SOLVER_BACKEND} --threads ${GPU_THREADS:-4} --workers 6,12,24 --batches 32,64,128 --write-config"
else
    echo "  dexbtx-miner benchmark                  # 2-min sweep across common batch sizes"
    echo "  dexbtx-miner benchmark --write-config   # write the winning config"
fi
echo "See TUNING.md for the env-var reference + per-GPU rough guidelines."
echo
