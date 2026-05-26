"""BTX Start helper CLI.

This is intentionally not a replacement for the real BTX node `btx-cli`.
Real wallet creation, signing, node RPC, and private-key custody must stay on
a backend machine running `btxd` + `btx-cli`.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

SITE_BASE_URL = "https://drinknile.com"
INSTALLER_URL = f"{SITE_BASE_URL}/install.sh"
STATS_URL = f"{SITE_BASE_URL}/stats-snapshot.json"
TREASURY_URL = f"{SITE_BASE_URL}/platform-treasury.json"
ADDRESS_RE = re.compile(r"^btx1z[0-9a-zA-Z]{50,}$")
WORKER_RE = re.compile(r"[^a-z0-9._-]", re.IGNORECASE)


def _sanitize_worker(worker: str) -> str:
    return WORKER_RE.sub("-", worker.strip() or "default")


def _validate_address(address: str) -> None:
    if not ADDRESS_RE.match(address):
        raise SystemExit("address does not match expected btx1z... format")


def _quote_flags(flags: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in flags)


def _installer_command(args: argparse.Namespace, *, preflight: bool) -> str:
    flags: list[str] = []
    if preflight:
        flags.append("--preflight")
    elif not args.address:
        raise SystemExit("--address is required for install-command")

    if args.address:
        _validate_address(args.address)
        flags.extend(["--address", args.address])

    flags.extend(["--worker", _sanitize_worker(args.worker)])

    if args.pool:
        flags.extend(["--pool", args.pool])

    if args.backend:
        flags.extend(["--solver-backend", args.backend])

    if args.local_solver:
        flags.extend(["--local-solver", args.local_solver])
        if args.trust_local_solver:
            flags.append("--trust-local-solver")

    if args.yes:
        flags.append("--yes")

    return f"curl -fsSL {shlex.quote(args.installer_url)} | bash -s -- {_quote_flags(flags)}"


def _load_json(url: str) -> dict[str, Any]:
    try:
        with urlopen(url, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise SystemExit(f"could not fetch {url}: {exc}") from exc


def _format_bps(bps: int | float | None) -> str:
    if bps is None:
        return "unknown"
    return f"{float(bps) / 100:.2f}%"


def _parse_time(value: str) -> datetime:
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise SystemExit("timestamp must be ISO-8601, for example 2026-05-26T09:15:00Z") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def cmd_install(args: argparse.Namespace) -> int:
    print(_installer_command(args, preflight=False))
    return 0


def cmd_preflight(args: argparse.Namespace) -> int:
    print(_installer_command(args, preflight=True))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    stats = _load_json(args.stats_url)
    treasury = _load_json(args.treasury_url)
    pool = stats.get("pool", {})
    policy = stats.get("policy", {})
    health = stats.get("health", {})
    btxd = health.get("btxd", {})

    print("BTX Start status")
    print(f"  site:              {SITE_BASE_URL}")
    print(f"  status:            {policy.get('status', 'unknown')}")
    print(f"  owned backend:     {policy.get('owned_backend_active', False)}")
    print(f"  stratum endpoint:  {policy.get('stratum_endpoint', 'unknown')}")
    print(f"  stats fetched at:  {stats.get('fetched_at', 'unknown')}")
    print(f"  workers now:       {pool.get('workers_active_now', 0)}")
    print(f"  shares 24h:        {pool.get('shares_24h', 0)}")
    print(f"  blocks 24h:        {pool.get('blocks_found_24h', 0)}")
    print(f"  node reachable:    {btxd.get('reachable', False)}")
    print(f"  fee policy:        {_format_bps(policy.get('trial_fee_bps'))} first {policy.get('trial_days', 0)}d, then {_format_bps(policy.get('post_trial_fee_bps'))}")
    print(f"  fee address:       {policy.get('fee_address') or treasury.get('platform_fee_address') or 'pending'}")
    return 0


def cmd_fee_preview(args: argparse.Namespace) -> int:
    policy_data = _load_json(args.stats_url).get("policy", {})
    first_share_at = _parse_time(args.first_share_at)
    now = _parse_time(args.now) if args.now else datetime.now(timezone.utc)

    trial_days = int(policy_data.get("trial_days", 7))
    trial_fee_bps = int(policy_data.get("trial_fee_bps", 0))
    post_trial_fee_bps = int(policy_data.get("post_trial_fee_bps", policy_data.get("pool_fee_bps", 50)))
    trial_end = first_share_at + timedelta(days=trial_days)
    fee_bps = trial_fee_bps if now < trial_end else post_trial_fee_bps
    platform_fee_sat = args.gross_sat * fee_bps // 10_000
    miner_payout_sat = args.gross_sat - platform_fee_sat

    print(json.dumps({
        "first_share_at": first_share_at.isoformat(),
        "trial_end_at": trial_end.isoformat(),
        "now": now.isoformat(),
        "fee_bps": fee_bps,
        "platform_fee_sat": platform_fee_sat,
        "miner_payout_sat": miner_payout_sat,
    }, indent=2))
    return 0


def _add_common_command_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--installer-url", default=INSTALLER_URL)
    parser.add_argument("--address")
    parser.add_argument("--worker", default="default")
    parser.add_argument("--pool")
    parser.add_argument("--backend", choices=["cuda", "metal", "mlx", "cpu"])
    parser.add_argument("--local-solver")
    parser.add_argument("--trust-local-solver", action="store_true")
    parser.add_argument("--yes", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="btxstart",
        description="BTX Start website helper CLI. Does not replace btx-cli.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    install = sub.add_parser("install-command", help="Print the BTX Start install command")
    _add_common_command_flags(install)
    install.set_defaults(func=cmd_install)

    preflight = sub.add_parser("preflight-command", help="Print the BTX Start preflight command")
    _add_common_command_flags(preflight)
    preflight.set_defaults(func=cmd_preflight)

    status = sub.add_parser("status", help="Print public BTX Start status")
    status.add_argument("--stats-url", default=STATS_URL)
    status.add_argument("--treasury-url", default=TREASURY_URL)
    status.set_defaults(func=cmd_status)

    fee = sub.add_parser("fee-preview", help="Preview the current public fee policy")
    fee.add_argument("--stats-url", default=STATS_URL)
    fee.add_argument("--first-share-at", required=True)
    fee.add_argument("--now")
    fee.add_argument("--gross-sat", type=int, required=True)
    fee.set_defaults(func=cmd_fee_preview)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
