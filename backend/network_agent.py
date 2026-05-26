"""BTX network observer for the managed mining backend.

The agent is intentionally conservative. By default it observes public peer
data and local btxd health, writes a snapshot, and records an event. It does
not mutate btxd peer state unless NETWORK_AGENT_APPLY_PEERS=true.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .btx_rpc import BtxRpcClient, BtxRpcError
from .repository import BackendRepository, iso
from .settings import BackendSettings


@dataclass(frozen=True)
class PeerCandidate:
    address: str
    score: float
    blocks_behind: int | None
    median_ping_ms: float | None
    country: str | None
    continent: str | None
    subver: str | None
    last_seen: int | None

    @property
    def is_synced(self) -> bool:
        return self.blocks_behind is None or self.blocks_behind <= 2


def fetch_json(url: str, timeout_s: float = 12.0) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": "btx-start-network-agent/0.1"})
    try:
        with urlopen(request, timeout=timeout_s) as response:
            return dict(json.loads(response.read().decode("utf-8")))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"peer source request failed: {exc}") from exc


def _float_or_none(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_or_none(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_peer_candidates(payload: dict[str, Any]) -> list[PeerCandidate]:
    peers = payload.get("peers")
    if not isinstance(peers, list):
        return []

    candidates: list[PeerCandidate] = []
    for peer in peers:
        if not isinstance(peer, dict):
            continue
        address = str(peer.get("addr") or "").strip()
        if not address:
            continue
        candidates.append(
            PeerCandidate(
                address=address,
                score=_float_or_none(peer.get("score")) or 0.0,
                blocks_behind=_int_or_none(peer.get("blocks_behind")),
                median_ping_ms=_float_or_none(peer.get("median_ping_ms")),
                country=str(peer.get("country") or "") or None,
                continent=str(peer.get("continent") or "") or None,
                subver=str(peer.get("subver") or "") or None,
                last_seen=_int_or_none(peer.get("last_seen")),
            )
        )
    return candidates


def select_peer_candidates(
    candidates: list[PeerCandidate],
    *,
    min_score: float,
    limit: int = 12,
) -> list[PeerCandidate]:
    eligible = [
        peer for peer in candidates
        if peer.score >= min_score and (peer.blocks_behind is None or peer.blocks_behind <= 10)
    ]
    return sorted(
        eligible,
        key=lambda peer: (
            not peer.is_synced,
            -(peer.score or 0),
            peer.median_ping_ms if peer.median_ping_ms is not None else 999_999,
            peer.address,
        ),
    )[:limit]


def read_node_state(rpc: BtxRpcClient) -> dict[str, Any]:
    state: dict[str, Any] = {"reachable": False}
    try:
        info = rpc.getblockchaininfo()
        state.update({
            "reachable": True,
            "blocks": info.get("blocks"),
            "headers": info.get("headers"),
            "initialblockdownload": info.get("initialblockdownload"),
            "verificationprogress": info.get("verificationprogress"),
        })
        try:
            state["connections"] = rpc.getconnectioncount()
        except BtxRpcError as exc:
            state["connections_error"] = str(exc)
    except BtxRpcError as exc:
        state["error"] = str(exc)
    return state


def maybe_apply_peers(rpc: BtxRpcClient, peers: list[PeerCandidate], *, enabled: bool) -> list[dict[str, Any]]:
    if not enabled:
        return []

    results: list[dict[str, Any]] = []
    for peer in peers:
        try:
            rpc.addnode(peer.address, "onetry")
            results.append({"address": peer.address, "status": "onetry"})
        except BtxRpcError as exc:
            results.append({"address": peer.address, "status": "error", "error": str(exc)})
    return results


def write_snapshot(path: str | Path, payload: dict[str, Any]) -> None:
    snapshot_path = Path(path)
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = snapshot_path.with_suffix(snapshot_path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    tmp_path.replace(snapshot_path)


def run_once(settings: BackendSettings) -> dict[str, Any]:
    settings.ensure_database_parent()
    repo = BackendRepository(settings.database_path)
    repo.init_db()
    rpc = BtxRpcClient(settings.btx_rpc_url, settings.btx_rpc_user, settings.btx_rpc_password)

    peer_payload = fetch_json(settings.network_agent_peer_url)
    candidates = normalize_peer_candidates(peer_payload)
    selected = select_peer_candidates(
        candidates,
        min_score=settings.network_agent_min_score,
    )
    node = read_node_state(rpc)
    applied = maybe_apply_peers(rpc, selected, enabled=settings.network_agent_apply_peers)

    snapshot = {
        "fetched_at": iso(),
        "source_url": settings.network_agent_peer_url,
        "mode": "observe_and_recommend" if not settings.network_agent_apply_peers else "observe_and_apply",
        "candidate_count": len(candidates),
        "recommended_peers": [asdict(peer) for peer in selected],
        "node": node,
        "applied": applied,
    }
    write_snapshot(settings.network_agent_snapshot_path, snapshot)
    repo.record_event("network_agent.snapshot", snapshot)
    return snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the BTX Start network observer agent")
    parser.add_argument("--once", action="store_true", help="run one poll and exit")
    args = parser.parse_args()
    settings = BackendSettings.from_env()

    while True:
        run_once(settings)
        if args.once:
            return 0
        time.sleep(max(10, settings.network_agent_interval_s))


if __name__ == "__main__":
    raise SystemExit(main())
