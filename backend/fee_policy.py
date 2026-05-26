"""BTX Start pool-fee policy helpers.

The pool backend should apply this policy during payout accounting, not inside
the public static site or the miner client. A miner can edit local config; the
backend is the only place that can enforce the trial window and fee routing.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


SATOSHIS_PER_BTX = 100_000_000


@dataclass(frozen=True)
class FeePolicy:
    """Per-payout-address trial, then disclosed platform fee."""

    trial_days: int = 7
    trial_fee_bps: int = 0
    post_trial_fee_bps: int = 50
    fee_address: str | None = None
    treasury_address: str | None = None
    account_key_scope: str = "payout_address"
    fee_routing: str = "pool_payout_accounting"

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "FeePolicy":
        return cls(
            trial_days=int(data.get("trial_days", data.get("intro_trial_days", cls.trial_days))),
            trial_fee_bps=int(data.get("trial_fee_bps", cls.trial_fee_bps)),
            post_trial_fee_bps=int(
                data.get(
                    "post_trial_fee_bps",
                    data.get("post_trial_pool_fee_bps", data.get("pool_fee_bps", cls.post_trial_fee_bps)),
                )
            ),
            fee_address=data.get("fee_address"),
            treasury_address=data.get("treasury_address"),
            account_key_scope=str(data.get("account_key_scope", cls.account_key_scope)),
            fee_routing=str(data.get("fee_routing", cls.fee_routing)),
        )

    @classmethod
    def from_file(cls, path: str | Path) -> "FeePolicy":
        payload = json.loads(Path(path).read_text())
        if "policy" in payload:
            return cls.from_mapping(payload["policy"])
        return cls.from_mapping(payload)

    def trial_end_at(self, first_share_at: datetime) -> datetime:
        return first_share_at + timedelta(days=self.trial_days)

    def effective_fee_bps(self, first_share_at: datetime, now: datetime | None = None) -> int:
        now = now or datetime.now(timezone.utc)
        first_share_at = _as_utc(first_share_at)
        now = _as_utc(now)
        if now < self.trial_end_at(first_share_at):
            return self.trial_fee_bps
        return self.post_trial_fee_bps

    def split_reward_sat(
        self,
        gross_reward_sat: int,
        first_share_at: datetime,
        now: datetime | None = None,
    ) -> dict[str, int]:
        if gross_reward_sat < 0:
            raise ValueError("gross_reward_sat cannot be negative")
        fee_bps = self.effective_fee_bps(first_share_at, now)
        fee_sat = gross_reward_sat * fee_bps // 10_000
        return {
            "fee_bps": fee_bps,
            "gross_reward_sat": gross_reward_sat,
            "platform_fee_sat": fee_sat,
            "miner_payout_sat": gross_reward_sat - fee_sat,
        }


def miner_account_key(payout_address: str) -> str:
    """Stable trial key.

    Keep this per payout address rather than per worker so a miner cannot reset
    a trial simply by changing `--worker`.
    """

    normalized = payout_address.strip()
    if not normalized:
        raise ValueError("payout_address is required")
    return normalized


def parse_timestamp(value: str) -> datetime:
    if value.endswith("Z"):
        value = f"{value[:-1]}+00:00"
    parsed = datetime.fromisoformat(value)
    return _as_utc(parsed)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate BTX Start fee policy for one payout")
    parser.add_argument("--policy", default="stats-snapshot.json", help="JSON policy source")
    parser.add_argument("--payout-address", required=True, help="Miner payout address")
    parser.add_argument("--first-share-at", required=True, help="ISO timestamp of first accepted share")
    parser.add_argument("--now", default=None, help="ISO timestamp to evaluate at")
    parser.add_argument("--gross-sat", type=int, default=SATOSHIS_PER_BTX, help="Gross payout in satoshis")
    args = parser.parse_args()

    policy = FeePolicy.from_file(args.policy)
    first_share_at = parse_timestamp(args.first_share_at)
    now = parse_timestamp(args.now) if args.now else datetime.now(timezone.utc)
    split = policy.split_reward_sat(args.gross_sat, first_share_at, now)
    result = {
        "account_key": miner_account_key(args.payout_address),
        "trial_end_at": policy.trial_end_at(first_share_at).isoformat(),
        "fee_address": policy.fee_address,
        "treasury_address": policy.treasury_address,
        "policy": asdict(policy),
        "split": split,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
