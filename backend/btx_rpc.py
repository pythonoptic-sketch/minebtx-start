"""Minimal BTX JSON-RPC client.

Keep this process on the backend private network. Never expose btxd RPC
directly to the public internet.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class BtxRpcError(RuntimeError):
    pass


@dataclass(frozen=True)
class BtxRpcClient:
    url: str
    username: str | None = None
    password: str | None = None
    timeout_s: float = 10.0

    def call(self, method: str, params: list[Any] | None = None, timeout_s: float | None = None) -> Any:
        body = json.dumps({
            "jsonrpc": "1.0",
            "id": "btx-start",
            "method": method,
            "params": params or [],
        }).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.username is not None and self.password is not None:
            token = f"{self.username}:{self.password}".encode("utf-8")
            headers["Authorization"] = f"Basic {base64.b64encode(token).decode('ascii')}"
        request = Request(self.url, data=body, headers=headers, method="POST")
        try:
            with urlopen(request, timeout=timeout_s or self.timeout_s) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise BtxRpcError(f"BTX RPC {method} failed: {exc}") from exc
        if payload.get("error"):
            raise BtxRpcError(f"BTX RPC {method} returned error: {payload['error']}")
        return payload.get("result")

    def getblockchaininfo(self) -> dict[str, Any]:
        return dict(self.call("getblockchaininfo"))

    def getnetworkhashps(self) -> int | float | None:
        return self.call("getnetworkhashps")

    def getconnectioncount(self) -> int:
        return int(self.call("getconnectioncount"))

    def getpeerinfo(self) -> list[dict[str, Any]]:
        return list(self.call("getpeerinfo"))

    def addnode(self, address: str, command: str = "onetry") -> Any:
        return self.call("addnode", [address, command])

    def getblocktemplate(self) -> dict[str, Any]:
        return dict(self.call("getblocktemplate", [{"rules": ["segwit"]}]))

    def getmatmulchallenge(self) -> dict[str, Any]:
        return dict(self.call("getmatmulchallenge"))

    def validateaddress(self, address: str) -> dict[str, Any]:
        return dict(self.call("validateaddress", [address]))

    def scantxoutset(
        self,
        scan_objects: list[str | dict[str, Any]],
        action: str = "start",
        timeout_s: float = 120.0,
    ) -> dict[str, Any]:
        return dict(self.call("scantxoutset", [action, scan_objects], timeout_s=timeout_s))

    def scantxoutset_address(self, address: str) -> dict[str, Any]:
        return self.scantxoutset([f"addr({address})"])

    def submitblock(self, block_hex: str) -> Any:
        return self.call("submitblock", [block_hex])

    def getnewaddress(self, label: str = "") -> str:
        return str(self.call("getnewaddress", [label]))

    def getbalance(self) -> Any:
        return self.call("getbalance")

    def sendmany(self, outputs: dict[str, float], comment: str = "BTX Start payout") -> str:
        return str(self.call("sendmany", ["", outputs, 1, comment]))
