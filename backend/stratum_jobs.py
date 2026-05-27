"""BTX MatMul stratum job construction."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any

from .block_builder import merkle_root_for_template
from .btx_rpc import BtxRpcClient


DEFAULT_SHARE_TARGET_HEX = "00000fffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"


def _clean_hex(value: str, *, length: int | None = None) -> str:
    text = str(value).strip().lower()
    if text.startswith("0x"):
        text = text[2:]
    if length is not None:
        text = text.zfill(length)
    return text


def target_to_work(target_hex: str) -> float:
    target = int(_clean_hex(target_hex), 16)
    if target <= 0:
        return 0.0
    return (2**256) / float(target + 1)


def compact_bits_to_target_hex(bits: str) -> str:
    """Convert Bitcoin-style compact nBits to a 256-bit target hex string."""

    bits_int = int(_clean_hex(bits), 16)
    exponent = bits_int >> 24
    mantissa = bits_int & 0x007FFFFF
    if bits_int & 0x00800000:
        raise ValueError("negative compact target is invalid")
    if exponent <= 3:
        target = mantissa >> (8 * (3 - exponent))
    else:
        target = mantissa << (8 * (exponent - 3))
    return f"{target:064x}"


@dataclass(frozen=True)
class PoolJob:
    job_id: str
    version: int
    previousblockhash: str
    merkleroot: str
    time: int
    bits: str
    block_target: str
    share_target: str
    height: int
    seed_a: str
    seed_b: str
    matmul_n: int
    matmul_b: int
    matmul_r: int
    epsilon_bits: int
    created_at: float
    block_template: dict[str, Any] | None = None
    coinbase_address: str | None = None
    address_script_pubkey_hex: str | None = None
    source: str = "getblocktemplate"

    @property
    def share_work(self) -> float:
        return target_to_work(self.share_target)

    def notify_params(self, *, clean_jobs: bool, nonce64_start: int) -> list[Any]:
        matmul_meta = {
            "seed_a": self.seed_a,
            "seed_b": self.seed_b,
            "block_height": self.height,
            "matmul_n": self.matmul_n,
            "matmul_b": self.matmul_b,
            "matmul_r": self.matmul_r,
            "epsilon_bits": self.epsilon_bits,
            "nonce64_start": nonce64_start,
        }
        return [
            self.job_id,
            self.version,
            self.previousblockhash,
            self.merkleroot,
            self.time,
            self.bits,
            self.share_target,
            clean_jobs,
            matmul_meta,
        ]


def job_from_matmul_challenge(payload: dict[str, Any], *, share_target_hex: str) -> PoolJob:
    ctx = dict(payload.get("header_context") or {})
    matmul = dict(payload.get("matmul") or {})
    height = int(payload.get("height") or matmul.get("height") or 0)
    bits = _clean_hex(ctx.get("bits") or payload["bits"], length=8)
    target = _clean_hex(payload.get("target") or compact_bits_to_target_hex(bits), length=64)
    prevhash = _clean_hex(ctx.get("previousblockhash") or payload["previousblockhash"], length=64)
    merkleroot = _clean_hex(ctx["merkleroot"], length=64)
    seed_a = _clean_hex(ctx.get("seed_a") or matmul["seed_a"], length=64)
    seed_b = _clean_hex(ctx.get("seed_b") or matmul["seed_b"], length=64)
    version = int(ctx.get("version") or payload["version"])
    ntime = int(ctx.get("time") or payload.get("curtime") or time.time())
    matmul_n = int(ctx.get("matmul_dim") or matmul.get("n") or payload.get("matmul_n") or 512)
    matmul_b = int(matmul.get("b") or payload.get("matmul_b") or 16)
    matmul_r = int(matmul.get("r") or payload.get("matmul_r") or 8)
    # BTX mainnet currently uses 18 epsilon bits. getmatmulchallenge exposes it
    # inside work_profile on newer nodes; keep a conservative fallback.
    work_profile = dict(payload.get("work_profile") or {})
    pre_hash = dict(work_profile.get("pre_hash_lottery") or {})
    epsilon_bits = int(pre_hash.get("epsilon_bits") or payload.get("epsilon_bits") or 18)
    share_target = _clean_hex(share_target_hex, length=64)
    return PoolJob(
        job_id=f"{height}:{prevhash[:16]}:{ntime}",
        version=version,
        previousblockhash=prevhash,
        merkleroot=merkleroot,
        time=ntime,
        bits=bits,
        block_target=target,
        share_target=share_target,
        height=height,
        seed_a=seed_a,
        seed_b=seed_b,
        matmul_n=matmul_n,
        matmul_b=matmul_b,
        matmul_r=matmul_r,
        epsilon_bits=epsilon_bits,
        created_at=time.time(),
    )


def job_from_block_template(
    template: dict[str, Any],
    *,
    share_target_hex: str,
    coinbase_address: str,
    address_script_pubkey_hex: str,
) -> PoolJob:
    payload = dict(template)
    payload["_merkle_root_hex_be"] = merkle_root_for_template(payload, address_script_pubkey_hex)
    bits = _clean_hex(payload["bits"], length=8)
    target = _clean_hex(payload.get("target") or compact_bits_to_target_hex(bits), length=64)
    prevhash = _clean_hex(payload["previousblockhash"], length=64)
    merkleroot = _clean_hex(payload["_merkle_root_hex_be"], length=64)
    seed_a = _clean_hex(payload["seed_a"], length=64)
    seed_b = _clean_hex(payload["seed_b"], length=64)
    height = int(payload["height"])
    ntime = int(payload["curtime"])
    return PoolJob(
        job_id=f"{height}:{prevhash[:16]}:{ntime}:{merkleroot[:16]}",
        version=int(payload["version"]),
        previousblockhash=prevhash,
        merkleroot=merkleroot,
        time=ntime,
        bits=bits,
        block_target=target,
        share_target=_clean_hex(share_target_hex, length=64),
        height=height,
        seed_a=seed_a,
        seed_b=seed_b,
        matmul_n=int(payload.get("matmul_n") or (payload.get("matmul") or {}).get("n") or 512),
        matmul_b=int(payload.get("matmul_b") or (payload.get("matmul") or {}).get("b") or 16),
        matmul_r=int(payload.get("matmul_r") or (payload.get("matmul") or {}).get("r") or 8),
        epsilon_bits=int(payload.get("epsilon_bits") or 18),
        created_at=time.time(),
        block_template=payload,
        coinbase_address=coinbase_address,
        address_script_pubkey_hex=address_script_pubkey_hex,
    )


class StratumJobManager:
    def __init__(
        self,
        rpc: BtxRpcClient,
        *,
        share_target_hex: str = DEFAULT_SHARE_TARGET_HEX,
        refresh_interval_s: int = 20,
        coinbase_address: str | None = None,
    ):
        self.rpc = rpc
        self.share_target_hex = share_target_hex
        self.refresh_interval_s = refresh_interval_s
        self.coinbase_address = coinbase_address
        self._address_script_pubkey_hex: str | None = None
        self._lock = asyncio.Lock()
        self._current: PoolJob | None = None
        self._last_refresh = 0.0

    @property
    def current_job(self) -> PoolJob | None:
        return self._current

    async def get_job(self, *, force: bool = False) -> PoolJob:
        async with self._lock:
            now = time.time()
            if (
                self._current is not None
                and not force
                and now - self._last_refresh < self.refresh_interval_s
            ):
                return self._current
            if not self.coinbase_address:
                raise RuntimeError("coinbase address is required for stratum jobs")
            if self._address_script_pubkey_hex is None:
                address_info = await asyncio.to_thread(self.rpc.validateaddress, self.coinbase_address)
                script = address_info.get("scriptPubKey")
                if not address_info.get("isvalid") or not script:
                    raise RuntimeError("coinbase address is not valid according to btxd")
                self._address_script_pubkey_hex = str(script)
            payload = await asyncio.to_thread(self.rpc.getblocktemplate)
            job = job_from_block_template(
                payload,
                share_target_hex=self.share_target_hex,
                coinbase_address=self.coinbase_address,
                address_script_pubkey_hex=self._address_script_pubkey_hex,
            )
            self._last_refresh = now
            self._current = job
            return job
