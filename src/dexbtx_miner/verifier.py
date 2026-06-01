"""Rental GPU verifier for BTX mining.

This tool is the "shovel" for rented compute: reject an instance unless it can
prove CUDA-capable BTX mining setup and measured economics below a configured
cost-per-BTX threshold. It does not trust GPU model names.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .economics import quote_verified_compute


@dataclass(frozen=True)
class LocalProof:
    solver_path: str
    solver_exists: bool
    solver_supports_daemon: bool
    solver_supports_share_target: bool
    requested_backend: str
    require_cuda: bool
    nvidia_smi_found: bool
    nvidia_gpus: list[str]
    zero_cpu_fallback_gate: bool
    errors: list[str]


@dataclass(frozen=True)
class RentalVerification:
    accepted: bool
    local_proof: LocalProof
    economics: dict[str, Any]
    reasons: list[str]


def _run(command: list[str], timeout: float = 10.0) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None


def _solver_help(path: str) -> str:
    proc = _run([path, "--help"], timeout=10)
    if proc is None:
        return ""
    return f"{proc.stdout}\n{proc.stderr}"


def _nvidia_smi() -> tuple[bool, list[str]]:
    path = shutil.which("nvidia-smi")
    if not path:
        return False, []
    proc = _run([
        path,
        "--query-gpu=name,driver_version,memory.total",
        "--format=csv,noheader",
    ], timeout=10)
    if proc is None or proc.returncode != 0:
        return True, []
    return True, [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def build_local_proof(
    *,
    solver_path: str,
    backend: str,
    require_cuda: bool,
) -> LocalProof:
    errors: list[str] = []
    solver = Path(solver_path).expanduser()
    solver_exists = solver.is_file()
    help_text = _solver_help(str(solver)) if solver_exists else ""
    supports_daemon = "--daemon" in help_text
    supports_share_target = "--share-target" in help_text
    nvidia_found, gpus = _nvidia_smi()
    if not solver_exists:
        errors.append(f"solver missing at {solver}")
    if not supports_daemon:
        errors.append("solver does not advertise --daemon")
    if not supports_share_target:
        errors.append("solver does not advertise --share-target")
    if require_cuda and backend != "cuda":
        errors.append("backend is not cuda")
    if require_cuda and not nvidia_found:
        errors.append("nvidia-smi not found")
    if require_cuda and nvidia_found and not gpus:
        errors.append("nvidia-smi found but no NVIDIA GPU row was returned")
    zero_cpu_gate = (
        solver_exists
        and supports_daemon
        and supports_share_target
        and (not require_cuda or (backend == "cuda" and nvidia_found and bool(gpus)))
    )
    return LocalProof(
        solver_path=str(solver),
        solver_exists=solver_exists,
        solver_supports_daemon=supports_daemon,
        solver_supports_share_target=supports_share_target,
        requested_backend=backend,
        require_cuda=require_cuda,
        nvidia_smi_found=nvidia_found,
        nvidia_gpus=gpus,
        zero_cpu_fallback_gate=zero_cpu_gate,
        errors=errors,
    )


def verify_rental(args: argparse.Namespace) -> RentalVerification:
    proof = build_local_proof(
        solver_path=args.gbt_solve,
        backend=args.backend,
        require_cuda=args.require_cuda,
    )
    economics = quote_verified_compute(
        measured_nps=args.measured_nps,
        network_nps=args.network_nps,
        hourly_usd=args.hourly_usd,
        fee_bps=args.fee_bps,
        max_cost_per_btx_usd=args.max_cost_per_btx,
        reference_buy_price_usd=args.reference_buy_price,
    ).to_dict()
    reasons = list(proof.errors)
    if not economics["clears_cost_gate"]:
        reasons.append(economics["recommendation"])
    accepted = proof.zero_cpu_fallback_gate and economics["clears_cost_gate"] and not economics.get("buy_beats_mine")
    if economics.get("buy_beats_mine"):
        reasons.append("quoted/OTC BTX is cheaper than mining this rental")
    return RentalVerification(
        accepted=accepted,
        local_proof=proof,
        economics=economics,
        reasons=reasons,
    )


def _print_human(result: RentalVerification) -> None:
    print("BTX rental GPU verifier")
    print(f"  decision: {'RENT' if result.accepted else 'REJECT'}")
    print(f"  backend: {result.local_proof.requested_backend}")
    print(f"  solver: {result.local_proof.solver_path}")
    print(f"  solver gates: daemon={result.local_proof.solver_supports_daemon} share-target={result.local_proof.solver_supports_share_target}")
    print(f"  nvidia-smi: {result.local_proof.nvidia_smi_found}")
    for gpu in result.local_proof.nvidia_gpus:
        print(f"    gpu: {gpu}")
    econ = result.economics
    print(f"  measured: {econ['measured_nps']:.0f} n/s")
    print(f"  yield: {econ['btx_per_hour']:.8f} BTX/h")
    if econ["cost_per_btx_usd"] is not None:
        print(f"  cost: ${econ['cost_per_btx_usd']:.4f}/BTX")
    print(f"  recommendation: {econ['recommendation']}")
    if result.reasons:
        print("  reasons:")
        for reason in result.reasons:
            print(f"    - {reason}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="dexbtx-miner verify-rental")
    ap.add_argument("--gbt-solve", default=str(Path.home() / ".dexbtx-miner" / "bin" / "btx-gbt-solve"))
    ap.add_argument("--backend", default="cuda", choices=["cuda", "metal", "mlx", "cpu"])
    ap.add_argument("--require-cuda", action="store_true", default=True)
    ap.add_argument("--measured-nps", type=float, required=True, help="Measured useful BTX hashrate in n/s")
    ap.add_argument("--network-nps", type=float, required=True, help="Current BTX network hashrate in n/s")
    ap.add_argument("--hourly-usd", type=float, required=True, help="Rental price in USD per hour")
    ap.add_argument("--max-cost-per-btx", type=float, default=1.0, help="Reject above this mined cost per BTX")
    ap.add_argument("--reference-buy-price", type=float, default=None, help="Optional live OTC/exchange BTX price")
    ap.add_argument("--fee-bps", type=int, default=50, help="Pool/platform fee basis points")
    ap.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = ap.parse_args(argv)
    result = verify_rental(args)
    if args.json:
        print(json.dumps(asdict(result), indent=2, sort_keys=True))
    else:
        _print_human(result)
    return 0 if result.accepted else 2


if __name__ == "__main__":
    sys.exit(main())
