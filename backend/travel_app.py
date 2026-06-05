"""FastAPI app for the Evarian travel order prototype."""

from __future__ import annotations

import os
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def database_path() -> Path:
    configured = os.environ.get("EVARIAN_DATABASE_PATH")
    if configured:
        return Path(configured)
    return Path(os.environ.get("DATA_DIR", "/var/lib/evarian")) / "evarian.sqlite3"


DB_PATH = database_path()
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS waitlist (
              id TEXT PRIMARY KEY,
              email TEXT NOT NULL UNIQUE,
              source TEXT,
              product TEXT,
              payload_json TEXT,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS trip_orders (
              id TEXT PRIMARY KEY,
              intent TEXT NOT NULL,
              wallet_cap INTEGER NOT NULL,
              risk_mode TEXT NOT NULL,
              route TEXT NOT NULL,
              score INTEGER NOT NULL,
              payload_json TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            """
        )


class WaitlistBody(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    source: Optional[str] = None
    product: Optional[str] = None
    joined_at: Optional[str] = None


class TripOrderBody(BaseModel):
    intent: str = Field(min_length=2, max_length=1200)
    wallet_cap: int = Field(default=250, ge=0, le=50000)
    risk_mode: str = Field(default="balanced", pattern="^(balanced|strict|fast)$")


app = FastAPI(title="Evarian Travel OS", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://drinknile.com", "https://www.drinknile.com", "http://localhost:8093"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
init_db()


def build_trip_order(intent: str, wallet_cap: int, risk_mode: str) -> dict[str, Any]:
    lowered = intent.lower()
    if "delay" in lowered or "miss" in lowered or "rebook" in lowered:
        route = "Recovery order"
        score = 91 if risk_mode != "strict" else 96
        status = "recovery_active"
        products = [
            {"kind": "monitoring", "label": "Delay, waiver, traffic, hotel risk", "state": "live"},
            {"kind": "flight", "label": "Replacement flight ranked by arrival time", "state": "ranked"},
            {"kind": "hotel", "label": "Late arrival message prepared", "state": "staged"},
            {"kind": "transfer", "label": "Pickup window moved", "state": "staged"},
        ]
    elif "tokyo" in lowered or "lisbon" in lowered or "trip" in lowered:
        route = "New trip order"
        score = 88
        status = "draft_order"
        products = [
            {"kind": "itinerary", "label": "Editable day-by-day plan", "state": "draft"},
            {"kind": "hotel", "label": "Stay options ranked by fit and cancellation window", "state": "ranked"},
            {"kind": "transport", "label": "Flight, rail, and transfer bundle", "state": "draft"},
            {"kind": "wallet", "label": f"Approval cap {wallet_cap}", "state": "pending"},
        ]
    else:
        route = "Change order"
        score = 94 if risk_mode != "fast" else 89
        status = "change_ready"
        products = [
            {"kind": "pnr", "label": "Reservation status checked", "state": "verified"},
            {"kind": "ticket", "label": "Open ticket coupon confirmed", "state": "verified"},
            {"kind": "emd", "label": "Seat and bag extras checked for transfer", "state": "protected"},
            {"kind": "wallet", "label": f"Auto-charge capped at {wallet_cap}", "state": "bounded"},
        ]

    return {
        "id": f"EV-{uuid4().hex[:8].upper()}",
        "status": status,
        "route": route,
        "score": score,
        "intent": intent,
        "wallet_cap": wallet_cap,
        "risk_mode": risk_mode,
        "products": products,
        "permissions": {
            "ask_before_non_refundable": True,
            "ask_before_forfeiting_credit": True,
            "auto_approve_under": wallet_cap,
        },
        "monitoring": ["flight_status", "fare_waiver", "weather", "traffic", "hotel_check_in"],
        "allowed_actions": ["hold", "modify", "cancel", "refund", "rebook", "escalate"],
    }


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "service": "evarian-travel-os",
        "database": str(DB_PATH),
        "time": utc_now(),
    }


@app.post("/api/waitlist")
def waitlist(body: WaitlistBody) -> dict[str, Any]:
    email = body.email.strip().lower()
    if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        raise HTTPException(status_code=400, detail="invalid email address")
    row_id = uuid4().hex
    payload_json = body.model_dump_json()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO waitlist(id, email, source, product, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
              source = excluded.source,
              product = excluded.product,
              payload_json = excluded.payload_json
            """,
            (
                row_id,
                email,
                body.source,
                body.product,
                payload_json,
                utc_now(),
            ),
        )
    return {"ok": True, "email": email}


@app.post("/api/trip-orders")
def create_trip_order(body: TripOrderBody) -> dict[str, Any]:
    order = build_trip_order(body.intent, body.wallet_cap, body.risk_mode)
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO trip_orders(id, intent, wallet_cap, risk_mode, route, score, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                order["id"],
                body.intent,
                body.wallet_cap,
                body.risk_mode,
                order["route"],
                order["score"],
                json.dumps(order, sort_keys=True),
                utc_now(),
            ),
        )
    return order
