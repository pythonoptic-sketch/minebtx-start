"""Economics helpers for verified BTX compute.

These helpers intentionally price measured work, not GPU model names. A rental
only clears the gate when the miner can prove useful BTX hashrate and the
resulting cost per BTX stays below the user's threshold.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


BLOCK_REWARD_BTX = 20.0
TARGET_BLOCK_SECONDS = 90.0
BLOCKS_PER_HOUR = 3600.0 / TARGET_BLOCK_SECONDS


@dataclass(frozen=True)
class VerifiedComputeQuote:
    measured_nps: float
    network_nps: float
    hourly_usd: float
    fee_bps: int
    btx_per_hour: float
    btx_per_day: float
    cost_per_btx_usd: float | None
    max_cost_per_btx_usd: float | None
    clears_cost_gate: bool
    reference_buy_price_usd: float | None
    buy_beats_mine: bool | None
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def estimate_btx_per_hour(
    measured_nps: float,
    network_nps: float,
    *,
    fee_bps: int = 0,
    block_reward_btx: float = BLOCK_REWARD_BTX,
    target_block_seconds: float = TARGET_BLOCK_SECONDS,
) -> float:
    if measured_nps <= 0 or network_nps <= 0 or target_block_seconds <= 0:
        return 0.0
    fee_multiplier = max(0.0, 1.0 - (fee_bps / 10_000.0))
    blocks_per_hour = 3600.0 / target_block_seconds
    return (measured_nps / network_nps) * block_reward_btx * blocks_per_hour * fee_multiplier


def quote_verified_compute(
    *,
    measured_nps: float,
    network_nps: float,
    hourly_usd: float,
    fee_bps: int = 0,
    max_cost_per_btx_usd: float | None = None,
    reference_buy_price_usd: float | None = None,
) -> VerifiedComputeQuote:
    btx_hour = estimate_btx_per_hour(measured_nps, network_nps, fee_bps=fee_bps)
    cost_per_btx = hourly_usd / btx_hour if btx_hour > 0 and hourly_usd >= 0 else None
    clears_cost_gate = (
        cost_per_btx is not None
        and max_cost_per_btx_usd is not None
        and cost_per_btx <= max_cost_per_btx_usd
    )
    buy_beats_mine = (
        cost_per_btx is not None
        and reference_buy_price_usd is not None
        and reference_buy_price_usd > 0
        and reference_buy_price_usd < cost_per_btx
    )
    if cost_per_btx is None:
        recommendation = "reject: measured hashrate or network reference is missing"
    elif buy_beats_mine:
        recommendation = "buy: quoted BTX is cheaper than mining this compute"
    elif max_cost_per_btx_usd is not None and not clears_cost_gate:
        recommendation = "reject: measured cost per BTX is above threshold"
    else:
        recommendation = "rent: measured compute clears the configured gate"
    return VerifiedComputeQuote(
        measured_nps=measured_nps,
        network_nps=network_nps,
        hourly_usd=hourly_usd,
        fee_bps=fee_bps,
        btx_per_hour=btx_hour,
        btx_per_day=btx_hour * 24.0,
        cost_per_btx_usd=cost_per_btx,
        max_cost_per_btx_usd=max_cost_per_btx_usd,
        clears_cost_gate=clears_cost_gate,
        reference_buy_price_usd=reference_buy_price_usd,
        buy_beats_mine=buy_beats_mine,
        recommendation=recommendation,
    )
