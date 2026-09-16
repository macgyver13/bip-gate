"""Build minimal synthetic PSBTv2 blobs for structural tests (no secrets)."""

from __future__ import annotations

import base64

from bip_gate.lanes.psbt_parse import (
    PSBT_GLOBAL_INPUT_COUNT,
    PSBT_GLOBAL_OUTPUT_COUNT,
    PSBT_GLOBAL_VERSION,
    PSBT_MAGIC,
    PSBT_OUT_SCRIPT,
    PSBT_OUT_SP_V0_INFO,
    PSBT_OUT_SP_V0_LABEL,
    build_map,
    _write_compact_size,
)


def _ck(keytype: int, keydata: bytes = b"") -> bytes:
    return bytes([keytype]) + keydata


def make_psbt_v2(
    *,
    outputs: list[dict],
    input_count: int = 1,
) -> bytes:
    """Build a minimal PSBTv2.

    Each output dict may include:
      - script: bytes | None
      - sp_info: bytes | None  (should be 66 bytes for valid)
      - sp_label: bytes | None (4 bytes LE)
    """
    global_entries = [
        (_ck(PSBT_GLOBAL_VERSION), (2).to_bytes(4, "little")),
        (_ck(PSBT_GLOBAL_INPUT_COUNT), _write_compact_size(input_count)),
        (_ck(PSBT_GLOBAL_OUTPUT_COUNT), _write_compact_size(len(outputs))),
    ]
    body = build_map(global_entries)
    for _ in range(input_count):
        body += build_map([])  # empty input maps
    for out in outputs:
        entries: list[tuple[bytes, bytes]] = []
        if out.get("script") is not None:
            entries.append((_ck(PSBT_OUT_SCRIPT), out["script"]))
        if out.get("sp_info") is not None:
            entries.append((_ck(PSBT_OUT_SP_V0_INFO), out["sp_info"]))
        if out.get("sp_label") is not None:
            entries.append((_ck(PSBT_OUT_SP_V0_LABEL), out["sp_label"]))
        body += build_map(entries)
    return PSBT_MAGIC + body


def fake_pubkey(tag: int) -> bytes:
    """33-byte fake compressed pubkey (NOT a valid curve point — structural only)."""
    return bytes([0x02]) + bytes([tag & 0xFF]) * 32


def sp_info_value(scan_tag: int = 1, spend_tag: int = 2) -> bytes:
    return fake_pubkey(scan_tag) + fake_pubkey(spend_tag)


def as_b64(psbt: bytes) -> str:
    return base64.b64encode(psbt).decode("ascii")


def as_hex(psbt: bytes) -> str:
    return psbt.hex()
