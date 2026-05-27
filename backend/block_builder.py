"""BTX block assembly helpers for accepted pool block candidates."""

from __future__ import annotations

import hashlib
import struct
from typing import Any


def sha256d(payload: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(payload).digest()).digest()


def hex_le_to_bytes(hex_be_display: str) -> bytes:
    return bytes.fromhex(hex_be_display)[::-1]


def varint(value: int) -> bytes:
    if value < 0xFD:
        return bytes([value])
    if value <= 0xFFFF:
        return b"\xfd" + struct.pack("<H", value)
    if value <= 0xFFFFFFFF:
        return b"\xfe" + struct.pack("<I", value)
    return b"\xff" + struct.pack("<Q", value)


def le16(value: int) -> bytes:
    return struct.pack("<H", value & 0xFFFF)


def le32(value: int) -> bytes:
    return struct.pack("<I", value & 0xFFFFFFFF)


def le64(value: int) -> bytes:
    return struct.pack("<Q", value & 0xFFFFFFFFFFFFFFFF)


def s32_le(value: int) -> bytes:
    return struct.pack("<i", value)


def s64_le(value: int) -> bytes:
    return struct.pack("<q", value)


def encode_pushdata_minimal_int(value: int) -> bytes:
    if value == 0:
        return b"\x00"
    if 1 <= value <= 16:
        return bytes([0x50 + value])
    out = bytearray()
    remaining = value
    while remaining:
        out.append(remaining & 0xFF)
        remaining >>= 8
    if out[-1] & 0x80:
        out.append(0)
    return bytes([len(out)]) + bytes(out)


def build_coinbase_tx(
    *,
    height: int,
    coinbase_value: int,
    address_script_pubkey_hex: str,
    witness_commitment_hex: str,
    tag: bytes = b"drinknile",
) -> tuple[bytes, bytes]:
    height_push = encode_pushdata_minimal_int(height)
    script_sig = height_push + bytes([len(tag)]) + tag
    txin = (
        b"\x00" * 32
        + b"\xff\xff\xff\xff"
        + varint(len(script_sig))
        + script_sig
        + b"\xff\xff\xff\xff"
    )

    address_script = bytes.fromhex(address_script_pubkey_hex)
    output0 = s64_le(coinbase_value) + varint(len(address_script)) + address_script

    witness_script = bytes.fromhex(witness_commitment_hex)
    output1 = s64_le(0) + varint(len(witness_script)) + witness_script

    witness_reserved = b"\x00" * 32
    witnesses = varint(1) + varint(len(witness_reserved)) + witness_reserved

    no_witness = s32_le(2) + varint(1) + txin + varint(2) + output0 + output1 + b"\x00\x00\x00\x00"
    txid_le = sha256d(no_witness)

    with_witness = (
        s32_le(2)
        + b"\x00\x01"
        + varint(1)
        + txin
        + varint(2)
        + output0
        + output1
        + witnesses
        + b"\x00\x00\x00\x00"
    )
    return with_witness, txid_le


def merkle_root_le_from_txids_be(txids_be_hex: list[str]) -> bytes:
    leaves = [bytes.fromhex(txid)[::-1] for txid in txids_be_hex]
    if len(leaves) == 1:
        return leaves[0]
    while len(leaves) > 1:
        if len(leaves) % 2 == 1:
            leaves.append(leaves[-1])
        leaves = [sha256d(leaves[i] + leaves[i + 1]) for i in range(0, len(leaves), 2)]
    return leaves[0]


def merkle_root_for_template(template: dict[str, Any], address_script_pubkey_hex: str) -> str:
    coinbase_full, txid_le = build_coinbase_tx(
        height=int(template["height"]),
        coinbase_value=int(template["coinbasevalue"]),
        address_script_pubkey_hex=address_script_pubkey_hex,
        witness_commitment_hex=str(template["default_witness_commitment"]),
    )
    del coinbase_full
    coinbase_txid_be = txid_le[::-1].hex()
    fee_txs = template.get("transactions", []) or []
    all_txids_be = [coinbase_txid_be] + [tx["txid"] for tx in fee_txs]
    return merkle_root_le_from_txids_be(all_txids_be)[::-1].hex()


def build_block_hex(
    template: dict[str, Any],
    *,
    address_script_pubkey_hex: str,
    nonce64: int,
    matmul_digest_hex: str,
    matrix_c_data_hex: str,
) -> str:
    coinbase_full, txid_le = build_coinbase_tx(
        height=int(template["height"]),
        coinbase_value=int(template["coinbasevalue"]),
        address_script_pubkey_hex=address_script_pubkey_hex,
        witness_commitment_hex=str(template["default_witness_commitment"]),
    )
    coinbase_txid_be = txid_le[::-1].hex()
    fee_txs = template.get("transactions", []) or []
    fee_tx_bytes = b"".join(bytes.fromhex(tx["data"]) for tx in fee_txs)
    all_txids_be = [coinbase_txid_be] + [tx["txid"] for tx in fee_txs]
    merkle_root_le = merkle_root_le_from_txids_be(all_txids_be)

    header = (
        s32_le(int(template["version"]))
        + hex_le_to_bytes(str(template["previousblockhash"]))
        + merkle_root_le
        + le32(int(template["curtime"]))
        + le32(int(str(template["bits"]), 16))
        + le64(nonce64)
        + bytes.fromhex(matmul_digest_hex)[::-1]
        + le16(int(template["matmul_n"]))
        + hex_le_to_bytes(str(template["seed_a"]))
        + hex_le_to_bytes(str(template["seed_b"]))
    )
    if len(header) != 182:
        raise ValueError(f"BTX header length was {len(header)}, expected 182")

    matrix_c_words = bytes.fromhex(matrix_c_data_hex)
    if len(matrix_c_words) % 4:
        raise ValueError("matrix_c_data_hex must contain 32-bit words")
    vtx = varint(1 + len(fee_txs)) + coinbase_full + fee_tx_bytes
    matrix_a = varint(0)
    matrix_b = varint(0)
    matrix_c = varint(len(matrix_c_words) // 4) + matrix_c_words
    return (header + vtx + matrix_a + matrix_b + matrix_c).hex()
