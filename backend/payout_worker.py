"""Payout planning worker.

Default mode is dry-run. Production execution should require an operator to
review the generated plan, verify the treasury address, unlock the payout
wallet, and run with `--execute`.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Any

from .btx_rpc import BtxRpcClient
from .repository import BackendRepository
from .settings import BackendSettings

SATOSHIS_PER_BTX = 100_000_000


def sat_to_btx(sat: int) -> float:
    return sat / SATOSHIS_PER_BTX


@dataclass(frozen=True)
class PayoutPlan:
    miner_outputs: dict[str, float]
    treasury_output: float
    treasury_address: str | None
    total_payable_sat: int
    total_fee_sat: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "miner_outputs": self.miner_outputs,
            "treasury_output": self.treasury_output,
            "treasury_address": self.treasury_address,
            "total_payable_sat": self.total_payable_sat,
            "total_fee_sat": self.total_fee_sat,
        }


def build_payout_plan(
    repo: BackendRepository,
    *,
    treasury_address: str | None,
    dust_floor_sat: int = 10_000,
) -> PayoutPlan:
    rows = repo.list_payable_balances(dust_floor_sat=dust_floor_sat)
    miner_outputs = {row["payout_address"]: sat_to_btx(int(row["payable_sat"])) for row in rows}
    total_payable_sat = sum(int(row["payable_sat"]) for row in rows)
    total_fee_sat = sum(int(row["fee_sat"]) for row in rows)
    return PayoutPlan(
        miner_outputs=miner_outputs,
        treasury_output=sat_to_btx(total_fee_sat) if total_fee_sat and treasury_address else 0.0,
        treasury_address=treasury_address,
        total_payable_sat=total_payable_sat,
        total_fee_sat=total_fee_sat,
    )


def execute_payout(plan: PayoutPlan, rpc: BtxRpcClient) -> str:
    if not plan.miner_outputs and not plan.treasury_output:
        raise ValueError("payout plan is empty")
    outputs = dict(plan.miner_outputs)
    if plan.treasury_output:
        if not plan.treasury_address:
            raise ValueError("treasury address is required when fee output is non-zero")
        outputs[plan.treasury_address] = outputs.get(plan.treasury_address, 0.0) + plan.treasury_output
    return rpc.sendmany(outputs)


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan or execute BTX Start payouts")
    parser.add_argument("--execute", action="store_true", help="Broadcast payout transaction")
    parser.add_argument("--dust-floor-sat", type=int, default=10_000)
    args = parser.parse_args()

    settings = BackendSettings.from_env()
    repo = BackendRepository(settings.database_path)
    repo.init_db()
    plan = build_payout_plan(
        repo,
        treasury_address=settings.treasury_address,
        dust_floor_sat=args.dust_floor_sat,
    )
    if not args.execute:
        print(json.dumps({"dry_run": True, "plan": plan.as_dict()}, indent=2, sort_keys=True))
        return 0
    rpc = BtxRpcClient(settings.btx_rpc_url, settings.btx_rpc_user, settings.btx_rpc_password)
    txid = execute_payout(plan, rpc)
    settled_count = repo.settle_payable_balances(txid=txid, dust_floor_sat=args.dust_floor_sat)
    print(json.dumps({
        "dry_run": False,
        "txid": txid,
        "settled_count": settled_count,
        "plan": plan.as_dict(),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
