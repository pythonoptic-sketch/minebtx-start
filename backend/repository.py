"""SQLite repository for BTX Start backend state."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .fee_policy import FeePolicy


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime | None = None) -> str:
    return (value or utc_now()).astimezone(timezone.utc).isoformat()


def parse_iso(value: str) -> datetime:
    if value.endswith("Z"):
        value = f"{value[:-1]}+00:00"
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class ShareRecord:
    payout_address: str
    worker_name: str
    job_id: str
    accepted: bool
    is_block: bool = False
    difficulty: float = 0
    reason: str | None = None
    created_at: datetime | None = None


@dataclass(frozen=True)
class RewardSplit:
    payout_address: str
    gross_sat: int
    fee_sat: int
    payable_sat: int
    fee_bps: int


class BackendRepository:
    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def init_db(self) -> None:
        schema_path = Path(__file__).with_name("schema.sql")
        with self.connect() as conn:
            conn.executescript(schema_path.read_text())

    def ensure_miner(self, payout_address: str, when: datetime | None = None) -> None:
        created_at = iso(when)
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO miners(payout_address, created_at)
                VALUES (?, ?)
                ON CONFLICT(payout_address) DO NOTHING
                """,
                (payout_address, created_at),
            )
            conn.execute(
                """
                INSERT INTO balances(payout_address, updated_at)
                VALUES (?, ?)
                ON CONFLICT(payout_address) DO NOTHING
                """,
                (payout_address, created_at),
            )

    def touch_worker(
        self,
        payout_address: str,
        worker_name: str,
        *,
        user_agent: str | None = None,
        when: datetime | None = None,
    ) -> None:
        self.ensure_miner(payout_address, when)
        seen = iso(when)
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO workers(payout_address, worker_name, last_seen_at, user_agent)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(payout_address, worker_name) DO UPDATE SET
                  last_seen_at = excluded.last_seen_at,
                  user_agent = COALESCE(excluded.user_agent, workers.user_agent)
                """,
                (payout_address, worker_name, seen, user_agent),
            )

    def record_share(self, share: ShareRecord) -> None:
        self.touch_worker(share.payout_address, share.worker_name, when=share.created_at)
        created_at = iso(share.created_at)
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO shares(
                  payout_address, worker_name, job_id, accepted, is_block,
                  difficulty, reason, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    share.payout_address,
                    share.worker_name,
                    share.job_id,
                    int(share.accepted),
                    int(share.is_block),
                    float(share.difficulty),
                    share.reason,
                    created_at,
                ),
            )
            if share.accepted:
                conn.execute(
                    """
                    UPDATE miners
                    SET first_share_at = COALESCE(first_share_at, ?)
                    WHERE payout_address = ?
                    """,
                    (created_at, share.payout_address),
                )

    def credit_reward(
        self,
        payout_address: str,
        gross_sat: int,
        policy: FeePolicy,
        *,
        when: datetime | None = None,
    ) -> RewardSplit:
        if gross_sat < 0:
            raise ValueError("gross_sat cannot be negative")
        self.ensure_miner(payout_address, when)
        now_iso = iso(when)
        with self.connect() as conn:
            miner = conn.execute(
                "SELECT first_share_at, created_at FROM miners WHERE payout_address = ?",
                (payout_address,),
            ).fetchone()
            first_share_at = parse_iso(miner["first_share_at"] or miner["created_at"])
            split = policy.split_reward_sat(gross_sat, first_share_at, when)
            fee_sat = split["platform_fee_sat"]
            payable_sat = split["miner_payout_sat"]
            fee_bps = split["fee_bps"]
            conn.execute(
                """
                UPDATE balances
                SET gross_sat = gross_sat + ?,
                    fee_sat = fee_sat + ?,
                    payable_sat = payable_sat + ?,
                    updated_at = ?
                WHERE payout_address = ?
                """,
                (gross_sat, fee_sat, payable_sat, now_iso, payout_address),
            )
            if fee_sat:
                conn.execute(
                    """
                    INSERT INTO fee_ledger(payout_address, fee_sat, fee_bps, treasury_address, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (payout_address, fee_sat, fee_bps, policy.treasury_address, now_iso),
                )
        return RewardSplit(payout_address, gross_sat, fee_sat, payable_sat, fee_bps)

    def stats(self) -> dict[str, Any]:
        cutoff_24h = iso(utc_now() - timedelta(days=1))
        cutoff_15m = iso(utc_now() - timedelta(minutes=15))
        with self.connect() as conn:
            pool = conn.execute(
                """
                SELECT
                  SUM(CASE WHEN accepted = 1 THEN 1 ELSE 0 END) AS shares_accepted,
                  SUM(CASE WHEN accepted = 0 THEN 1 ELSE 0 END) AS shares_rejected,
                  SUM(CASE WHEN accepted = 1 AND created_at >= ? THEN 1 ELSE 0 END) AS shares_24h,
                  SUM(CASE WHEN is_block = 1 AND created_at >= ? THEN 1 ELSE 0 END) AS blocks_24h
                FROM shares
                """,
                (cutoff_24h, cutoff_24h),
            ).fetchone()
            workers_now = conn.execute(
                """
                SELECT COUNT(*) AS n
                FROM workers
                WHERE last_seen_at >= ?
                """,
                (cutoff_15m,),
            ).fetchone()["n"]
            totals = conn.execute(
                """
                SELECT
                  COALESCE(SUM(gross_sat), 0) AS gross_sat,
                  COALESCE(SUM(fee_sat), 0) AS fee_sat,
                  COALESCE(SUM(payable_sat), 0) AS payable_sat
                FROM balances
                """
            ).fetchone()
        return {
            "workers_active_now": int(workers_now or 0),
            "shares_accepted_total": int(pool["shares_accepted"] or 0),
            "shares_rejected_total": int(pool["shares_rejected"] or 0),
            "shares_24h": int(pool["shares_24h"] or 0),
            "blocks_found_24h": int(pool["blocks_24h"] or 0),
            "gross_sat": int(totals["gross_sat"] or 0),
            "pending_fee_sat": int(totals["fee_sat"] or 0),
            "pending_miner_payout_sat": int(totals["payable_sat"] or 0),
        }

    def miner_dashboard(self, payout_address: str) -> dict[str, Any]:
        cutoff_24h = iso(utc_now() - timedelta(days=1))
        with self.connect() as conn:
            miner = conn.execute(
                "SELECT payout_address, first_share_at, created_at FROM miners WHERE payout_address = ?",
                (payout_address,),
            ).fetchone()
            if miner is None:
                return {
                    "payout_address": payout_address,
                    "known": False,
                    "workers": [],
                    "balance": {"gross_sat": 0, "fee_sat": 0, "payable_sat": 0},
                }
            balance = conn.execute(
                "SELECT gross_sat, fee_sat, payable_sat, updated_at FROM balances WHERE payout_address = ?",
                (payout_address,),
            ).fetchone()
            workers = conn.execute(
                """
                SELECT worker_name, last_seen_at, user_agent
                FROM workers
                WHERE payout_address = ?
                ORDER BY last_seen_at DESC
                """,
                (payout_address,),
            ).fetchall()
            share_stats = conn.execute(
                """
                SELECT
                  SUM(CASE WHEN accepted = 1 THEN 1 ELSE 0 END) AS accepted,
                  SUM(CASE WHEN accepted = 0 THEN 1 ELSE 0 END) AS rejected,
                  SUM(CASE WHEN accepted = 1 AND created_at >= ? THEN 1 ELSE 0 END) AS accepted_24h
                FROM shares
                WHERE payout_address = ?
                """,
                (cutoff_24h, payout_address),
            ).fetchone()
        return {
            "payout_address": payout_address,
            "known": True,
            "first_share_at": miner["first_share_at"],
            "created_at": miner["created_at"],
            "workers": [dict(row) for row in workers],
            "shares": dict(share_stats),
            "balance": dict(balance) if balance else {"gross_sat": 0, "fee_sat": 0, "payable_sat": 0},
        }

    def list_payable_balances(self, *, dust_floor_sat: int) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT payout_address, gross_sat, fee_sat, payable_sat, updated_at
                FROM balances
                WHERE payable_sat >= ?
                ORDER BY payable_sat DESC
                """,
                (dust_floor_sat,),
            ).fetchall()
        return [dict(row) for row in rows]

    def settle_payable_balances(self, *, txid: str, dust_floor_sat: int) -> int:
        rows = self.list_payable_balances(dust_floor_sat=dust_floor_sat)
        if not rows:
            return 0
        now_iso = iso()
        with self.connect() as conn:
            for row in rows:
                conn.execute(
                    """
                    INSERT INTO payouts(
                      payout_address, gross_sat, fee_sat, paid_sat, txid, status, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, 'sent', ?)
                    """,
                    (
                        row["payout_address"],
                        int(row["gross_sat"]),
                        int(row["fee_sat"]),
                        int(row["payable_sat"]),
                        txid,
                        now_iso,
                    ),
                )
                conn.execute(
                    """
                    UPDATE balances
                    SET gross_sat = 0,
                        fee_sat = 0,
                        payable_sat = 0,
                        updated_at = ?
                    WHERE payout_address = ?
                    """,
                    (now_iso, row["payout_address"]),
                )
        return len(rows)

    def record_event(self, event_type: str, payload: dict[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO backend_events(event_type, payload_json, created_at)
                VALUES (?, ?, ?)
                """,
                (event_type, json.dumps(payload, sort_keys=True), iso()),
            )

    def upsert_subscription(
        self,
        *,
        account_id: str,
        status: str,
        stripe_customer_id: str | None = None,
        stripe_subscription_id: str | None = None,
        trial_end: str | None = None,
        current_period_end: str | None = None,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO accounts(id, created_at)
                VALUES (?, ?)
                ON CONFLICT(id) DO NOTHING
                """,
                (account_id, iso()),
            )
            conn.execute(
                """
                INSERT INTO subscriptions(
                  account_id, stripe_customer_id, stripe_subscription_id,
                  status, trial_end, current_period_end, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(account_id) DO UPDATE SET
                  stripe_customer_id = COALESCE(excluded.stripe_customer_id, subscriptions.stripe_customer_id),
                  stripe_subscription_id = COALESCE(excluded.stripe_subscription_id, subscriptions.stripe_subscription_id),
                  status = excluded.status,
                  trial_end = excluded.trial_end,
                  current_period_end = excluded.current_period_end,
                  updated_at = excluded.updated_at
                """,
                (
                    account_id,
                    stripe_customer_id,
                    stripe_subscription_id,
                    status,
                    trial_end,
                    current_period_end,
                    iso(),
                ),
            )
