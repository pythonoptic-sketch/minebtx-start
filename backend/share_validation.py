"""Share validation backends for the BTX stratum service."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from .stratum_jobs import PoolJob, compact_bits_to_target_hex


@dataclass(frozen=True)
class SubmittedShare:
    job_id: str
    nonce: int
    ntime: int
    extranonce2: str


@dataclass(frozen=True)
class ValidationResult:
    accepted: bool
    reason: str | None = None
    is_block: bool = False
    difficulty: float = 0.0
    digest_hex: str | None = None
    raw_output: dict[str, Any] | None = None


class DisabledShareValidator:
    async def validate(self, job: PoolJob, share: SubmittedShare) -> ValidationResult:
        return ValidationResult(False, "share validator is not configured")


class SolverShareValidator:
    """Validate submitted shares by re-running the patched BTX solver.

    This is slower than an in-process verifier, but it is deterministic and
    safe as a first production gate because accepted shares have to reproduce
    the exact submitted nonce against the job's share target.
    """

    def __init__(
        self,
        solver_path: str,
        *,
        backend: str = "cpu",
        solver_threads: int = 2,
        batch_size: int = 2,
        max_tries: int = 8,
        max_seconds: float = 10.0,
    ):
        from dexbtx_miner.gbt_solve_wrapper import GbtSolveWrapper, SolverEnv

        self.max_tries = max_tries
        self.max_seconds = max_seconds
        self._wrapper = GbtSolveWrapper(
            solver_path,
            backend=backend,
            solver_threads=solver_threads,
            batch_size=batch_size,
            solver_env=SolverEnv(backend=backend, solver_threads=solver_threads, batch_size=batch_size),
        )

    async def validate(self, job: PoolJob, share: SubmittedShare) -> ValidationResult:
        if share.ntime != job.time:
            return ValidationResult(False, "ntime does not match current job")
        from dexbtx_miner.gbt_solve_wrapper import SolveChallenge

        challenge = SolveChallenge(
            version=job.version,
            prev_hash=job.previousblockhash,
            merkle_root=job.merkleroot,
            time=job.time,
            bits=job.bits,
            seed_a=job.seed_a,
            seed_b=job.seed_b,
            block_height=job.height,
            matmul_n=job.matmul_n,
            matmul_b=job.matmul_b,
            matmul_r=job.matmul_r,
            epsilon_bits=job.epsilon_bits,
            share_target_hex=job.share_target,
        )
        result = await self._wrapper.solve_slice(
            challenge,
            nonce_start=share.nonce,
            max_tries=self.max_tries,
            max_seconds=self.max_seconds,
        )
        if not result.found:
            return ValidationResult(False, "digest >= share target", raw_output=result.raw_output)
        if result.nonce != share.nonce:
            return ValidationResult(False, "solver did not reproduce submitted nonce", raw_output=result.raw_output)
        digest_hex = (result.digest_hex or "").lower()
        is_block = False
        if digest_hex:
            block_target = int(job.block_target or compact_bits_to_target_hex(job.bits), 16)
            is_block = int(digest_hex, 16) <= block_target
        return ValidationResult(
            True,
            is_block=is_block,
            difficulty=job.share_work,
            digest_hex=digest_hex or None,
            raw_output=result.raw_output,
        )


def build_share_validator(settings: Any) -> DisabledShareValidator | SolverShareValidator:
    mode = str(getattr(settings, "share_validation_mode", "disabled")).strip().lower()
    if mode in {"solver", "external-solver"}:
        return SolverShareValidator(
            getattr(settings, "share_validation_solver_path"),
            backend=getattr(settings, "share_validation_backend"),
            solver_threads=getattr(settings, "share_validation_solver_threads"),
            batch_size=getattr(settings, "share_validation_batch_size"),
            max_tries=getattr(settings, "share_validation_max_tries"),
            max_seconds=getattr(settings, "share_validation_max_seconds"),
        )
    return DisabledShareValidator()
