"""Minimal PSBT map parser (stdlib only).

Sufficient for structural BIP375 checks: detect PSBT, walk global/input/output
maps, and report per-output key types. Not a full PSBT library.
"""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass, field


PSBT_MAGIC = b"psbt\xff"

# BIP370
PSBT_GLOBAL_UNSIGNED_TX = 0x00
PSBT_GLOBAL_VERSION = 0x02
PSBT_GLOBAL_INPUT_COUNT = 0x04
PSBT_GLOBAL_OUTPUT_COUNT = 0x05

# BIP370 per-output
PSBT_OUT_AMOUNT = 0x03
PSBT_OUT_SCRIPT = 0x04

# BIP375 per-output (from bip-0375.mediawiki)
# PSBT_OUT_SP_V0_INFO = 0x09 — Silent Payment Data (scan+spend keys)
# PSBT_OUT_SP_V0_LABEL = 0x0a
PSBT_OUT_SP_V0_INFO = 0x09
PSBT_OUT_SP_V0_LABEL = 0x0a

# BIP375 global (for heuristic SP detection)
PSBT_GLOBAL_SP_ECDH_SHARE = 0x07
PSBT_GLOBAL_SP_DLEQ = 0x08


class PsbtParseError(ValueError):
    """Raised when bytes cannot be interpreted as a PSBT."""


def _read_compact_size(data: bytes, i: int) -> tuple[int, int]:
    if i >= len(data):
        raise PsbtParseError("truncated compact size")
    first = data[i]
    i += 1
    if first < 0xFD:
        return first, i
    if first == 0xFD:
        if i + 2 > len(data):
            raise PsbtParseError("truncated compact size (uint16)")
        return int.from_bytes(data[i : i + 2], "little"), i + 2
    if first == 0xFE:
        if i + 4 > len(data):
            raise PsbtParseError("truncated compact size (uint32)")
        return int.from_bytes(data[i : i + 4], "little"), i + 4
    if i + 8 > len(data):
        raise PsbtParseError("truncated compact size (uint64)")
    return int.from_bytes(data[i : i + 8], "little"), i + 8


def _write_compact_size(n: int) -> bytes:
    if n < 0xFD:
        return bytes([n])
    if n <= 0xFFFF:
        return b"\xfd" + n.to_bytes(2, "little")
    if n <= 0xFFFFFFFF:
        return b"\xfe" + n.to_bytes(4, "little")
    return b"\xff" + n.to_bytes(8, "little")


def decode_psbt_bytes(raw: str | bytes) -> bytes:
    """Accept base64, hex, or raw bytes; return PSBT binary."""
    if isinstance(raw, bytes):
        data = raw
    else:
        s = raw.strip()
        data = None
        # Try hex first if it looks like hex
        try:
            if all(c in "0123456789abcdefABCDEF" for c in s) and len(s) % 2 == 0:
                data = binascii.unhexlify(s)
        except (binascii.Error, ValueError):
            data = None
        if data is None:
            try:
                data = base64.b64decode(s, validate=False)
            except (binascii.Error, ValueError) as exc:
                raise PsbtParseError(f"not valid base64 or hex: {exc}") from exc
    if not data.startswith(PSBT_MAGIC):
        raise PsbtParseError("missing PSBT magic bytes (psbt\\xff)")
    return data


@dataclass
class PsbtMap:
    """One PSBT key-value map (global, input, or output)."""

    entries: list[tuple[bytes, bytes]] = field(default_factory=list)

    def key_types(self) -> set[int]:
        types: set[int] = set()
        for key, _ in self.entries:
            if key:
                types.add(key[0])
        return types

    def values_for_type(self, keytype: int) -> list[bytes]:
        out: list[bytes] = []
        for key, val in self.entries:
            if key and key[0] == keytype:
                out.append(val)
        return out

    def has_type(self, keytype: int) -> bool:
        return keytype in self.key_types()


@dataclass
class ParsedPsbt:
    global_map: PsbtMap
    inputs: list[PsbtMap]
    outputs: list[PsbtMap]
    psbt_version: int | None  # None if absent (v0)

    @property
    def is_v2(self) -> bool:
        # BIP370: explicit version field, or v2-only globals present
        if self.psbt_version is not None:
            return self.psbt_version >= 2
        gtypes = self.global_map.key_types()
        return (
            PSBT_GLOBAL_INPUT_COUNT in gtypes
            or PSBT_GLOBAL_OUTPUT_COUNT in gtypes
            or PSBT_OUT_SCRIPT in {t for m in self.outputs for t in m.key_types()}
        )


def _parse_map(data: bytes, i: int) -> tuple[PsbtMap, int]:
    entries: list[tuple[bytes, bytes]] = []
    while True:
        if i >= len(data):
            raise PsbtParseError("truncated map (no separator)")
        key_len, i = _read_compact_size(data, i)
        if key_len == 0:
            break
        if i + key_len > len(data):
            raise PsbtParseError("truncated key")
        key = data[i : i + key_len]
        i += key_len
        val_len, i = _read_compact_size(data, i)
        if i + val_len > len(data):
            raise PsbtParseError("truncated value")
        val = data[i : i + val_len]
        i += val_len
        entries.append((key, val))
    return PsbtMap(entries=entries), i


def _count_vin_vout(unsigned_tx: bytes) -> tuple[int, int]:
    """Minimal non-witness tx header parse for vin/vout counts."""
    if len(unsigned_tx) < 5:
        raise PsbtParseError("unsigned tx too short")
    i = 4  # skip version
    # Reject witness marker (should not appear in PSBT unsigned tx)
    if i + 2 <= len(unsigned_tx) and unsigned_tx[i] == 0x00 and unsigned_tx[i + 1] == 0x01:
        raise PsbtParseError("witness serialization not allowed for PSBT unsigned tx")
    vin_count, i = _read_compact_size(unsigned_tx, i)
    for _ in range(vin_count):
        if i + 36 > len(unsigned_tx):
            raise PsbtParseError("truncated vin")
        i += 36  # prevout
        script_len, i = _read_compact_size(unsigned_tx, i)
        i += script_len
        if i + 4 > len(unsigned_tx):
            raise PsbtParseError("truncated vin sequence")
        i += 4
    vout_count, i = _read_compact_size(unsigned_tx, i)
    for _ in range(vout_count):
        if i + 8 > len(unsigned_tx):
            raise PsbtParseError("truncated vout")
        i += 8
        script_len, i = _read_compact_size(unsigned_tx, i)
        i += script_len
    return vin_count, vout_count


def parse_psbt(raw: str | bytes) -> ParsedPsbt:
    data = decode_psbt_bytes(raw)
    i = len(PSBT_MAGIC)
    global_map, i = _parse_map(data, i)

    psbt_version: int | None = None
    ver_vals = global_map.values_for_type(PSBT_GLOBAL_VERSION)
    if ver_vals:
        if len(ver_vals[0]) != 4:
            raise PsbtParseError("invalid PSBT_GLOBAL_VERSION length")
        psbt_version = int.from_bytes(ver_vals[0], "little")

    in_count: int | None = None
    out_count: int | None = None

    in_vals = global_map.values_for_type(PSBT_GLOBAL_INPUT_COUNT)
    out_vals = global_map.values_for_type(PSBT_GLOBAL_OUTPUT_COUNT)
    if in_vals:
        in_count, _ = _read_compact_size(in_vals[0], 0)
    if out_vals:
        out_count, _ = _read_compact_size(out_vals[0], 0)

    if in_count is None or out_count is None:
        utx = global_map.values_for_type(PSBT_GLOBAL_UNSIGNED_TX)
        if utx:
            vin, vout = _count_vin_vout(utx[0])
            in_count = in_count if in_count is not None else vin
            out_count = out_count if out_count is not None else vout

    if in_count is None or out_count is None:
        # Last resort: consume remaining maps; cannot split inputs vs outputs
        # without counts — fail closed for structural SP checks.
        raise PsbtParseError(
            "cannot determine input/output counts "
            "(need PSBTv2 counts or PSBT_GLOBAL_UNSIGNED_TX)"
        )

    inputs: list[PsbtMap] = []
    for _ in range(in_count):
        m, i = _parse_map(data, i)
        inputs.append(m)
    outputs: list[PsbtMap] = []
    for _ in range(out_count):
        m, i = _parse_map(data, i)
        outputs.append(m)

    return ParsedPsbt(
        global_map=global_map,
        inputs=inputs,
        outputs=outputs,
        psbt_version=psbt_version,
    )


def build_kv(key: bytes, value: bytes) -> bytes:
    return _write_compact_size(len(key)) + key + _write_compact_size(len(value)) + value


def build_map(entries: list[tuple[bytes, bytes]]) -> bytes:
    parts = [build_kv(k, v) for k, v in entries]
    return b"".join(parts) + b"\x00"


def looks_like_psbt(raw: str | None) -> bool:
    if not raw or not raw.strip():
        return False
    try:
        decode_psbt_bytes(raw)
        return True
    except PsbtParseError:
        return False
