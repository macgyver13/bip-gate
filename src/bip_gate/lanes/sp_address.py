"""Minimal Bech32m (BIP173/350) + BIP352 silent payment address decode.

Stdlib only. Encoding of silent payment addresses uses Bech32m for all
versions (BIP352), including version 0 (unlike BIP350 segwit rules).
"""

from __future__ import annotations

from dataclasses import dataclass

# BIP173 charset
_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
_CHARSET_MAP = {c: i for i, c in enumerate(_CHARSET)}

# BIP173 generator
_GEN = [0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3]

# BIP350 Bech32m constant (Bech32 uses 1)
_BECH32M_CONST = 0x2BC830A3

_VALID_HRPS = frozenset({"sp", "tsp"})


class SpAddressError(ValueError):
    """Silent payment address decode / structural failure."""


def _polymod(values: list[int]) -> int:
    chk = 1
    for v in values:
        b = chk >> 25
        chk = (chk & 0x1FFFFFF) << 5 ^ v
        for i in range(5):
            chk ^= _GEN[i] if ((b >> i) & 1) else 0
    return chk


def _hrp_expand(hrp: str) -> list[int]:
    return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]


def _verify_checksum(hrp: str, data: list[int]) -> bool:
    return _polymod(_hrp_expand(hrp) + data) == _BECH32M_CONST


def _create_checksum(hrp: str, data: list[int]) -> list[int]:
    values = _hrp_expand(hrp) + data
    polymod = _polymod(values + [0, 0, 0, 0, 0, 0]) ^ _BECH32M_CONST
    return [(polymod >> 5 * (5 - i)) & 31 for i in range(6)]


def convertbits(
    data: list[int] | bytes, frombits: int, tobits: int, *, pad: bool = True
) -> list[int] | None:
    """Power-of-2 base conversion (BIP173)."""
    acc = 0
    bits = 0
    ret: list[int] = []
    maxv = (1 << tobits) - 1
    max_acc = (1 << (frombits + tobits - 1)) - 1
    for value in data:
        if value < 0 or (value >> frombits):
            return None
        acc = ((acc << frombits) | value) & max_acc
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            ret.append((acc >> bits) & maxv)
    if pad:
        if bits:
            ret.append((acc << (tobits - bits)) & maxv)
    elif bits >= frombits or ((acc << (tobits - bits)) & maxv):
        return None
    return ret


def bech32m_decode(addr: str) -> tuple[str, list[int]]:
    """Decode a Bech32m string → (hrp, data_values_without_checksum).

    Silent payment addresses exceed BIP173's 90-character segwit limit;
    BIP352 recommends allowing up to 1023 characters. Fail closed on
    mixed case, bad charset, missing separator, or bad checksum.
    """
    if not addr or not isinstance(addr, str):
        raise SpAddressError("empty address")
    if any(ord(c) < 33 or ord(c) > 126 for c in addr):
        raise SpAddressError("address contains non-printable ASCII")
    if addr.lower() != addr and addr.upper() != addr:
        raise SpAddressError("mixed case address")
    if len(addr) > 1023:
        raise SpAddressError("address exceeds BIP352 recommended max length")

    bech = addr.lower()
    pos = bech.rfind("1")
    if pos < 1 or pos + 7 > len(bech):
        raise SpAddressError("missing or misplaced Bech32 separator")

    hrp = bech[:pos]
    data_part = bech[pos + 1 :]
    if not all(c in _CHARSET_MAP for c in data_part):
        raise SpAddressError("invalid Bech32 character")

    data = [_CHARSET_MAP[c] for c in data_part]
    if not _verify_checksum(hrp, data):
        raise SpAddressError("invalid Bech32m checksum")

    return hrp, data[:-6]


def bech32m_encode(hrp: str, data: list[int]) -> str:
    """Encode HRP + data values as Bech32m (for tests / vectors)."""
    combined = data + _create_checksum(hrp, data)
    return hrp + "1" + "".join(_CHARSET[d] for d in combined)


@dataclass(frozen=True)
class SilentPaymentAddress:
    """Decoded BIP352 silent payment address (structural fields only)."""

    hrp: str
    version: int
    scan_pubkey: bytes  # 33-byte compressed
    spend_pubkey: bytes  # 33-byte compressed B_m

    @property
    def payload(self) -> bytes:
        return self.scan_pubkey + self.spend_pubkey


def _check_compressed_pubkey(pk: bytes, label: str) -> None:
    if len(pk) != 33:
        raise SpAddressError(f"{label} length {len(pk)} != 33")
    if pk[0] not in (0x02, 0x03):
        raise SpAddressError(
            f"{label} must be compressed (prefix 0x02 or 0x03), got 0x{pk[0]:02x}"
        )


def decode_silent_payment_address(addr: str) -> SilentPaymentAddress:
    """Decode and structurally validate a BIP352 silent payment address.

    Checks (fail closed):
    - Bech32m checksum
    - HRP is ``sp`` (mainnet) or ``tsp`` (testnet)
    - Version witness program character for v0 is ``q`` (value 0)
    - Data after version is exactly 66 bytes = B_scan (33) || B_m (33)
    - Each compressed pubkey starts with 0x02 or 0x03
    """
    hrp, data = bech32m_decode(addr)
    if hrp not in _VALID_HRPS:
        raise SpAddressError(f"HRP must be 'sp' or 'tsp', got {hrp!r}")
    if not data:
        raise SpAddressError("empty data part")

    version = data[0]
    # BIP352: v0 only for this structural checker (version char 'q')
    if version != 0:
        raise SpAddressError(
            f"unsupported silent payment version {version} "
            f"(structural checker implements v0 only; expected 'q')"
        )

    decoded = convertbits(data[1:], 5, 8, pad=False)
    if decoded is None:
        raise SpAddressError("invalid 5-to-8 bit conversion / padding")
    payload = bytes(decoded)

    # BIP352: v0 data part must be exactly 66 bytes
    if len(payload) != 66:
        raise SpAddressError(
            f"v0 silent payment payload length {len(payload)} != 66"
        )

    scan = payload[:33]
    spend = payload[33:]
    _check_compressed_pubkey(scan, "B_scan")
    _check_compressed_pubkey(spend, "B_m")

    return SilentPaymentAddress(
        hrp=hrp,
        version=version,
        scan_pubkey=scan,
        spend_pubkey=spend,
    )


def encode_silent_payment_address(
    scan_pubkey: bytes,
    spend_pubkey: bytes,
    *,
    hrp: str = "sp",
    version: int = 0,
) -> str:
    """Encode a v0 silent payment address (test helper)."""
    if hrp not in _VALID_HRPS:
        raise SpAddressError(f"HRP must be 'sp' or 'tsp', got {hrp!r}")
    _check_compressed_pubkey(scan_pubkey, "B_scan")
    _check_compressed_pubkey(spend_pubkey, "B_m")
    prog = convertbits(scan_pubkey + spend_pubkey, 8, 5, pad=True)
    if prog is None:
        raise SpAddressError("8-to-5 conversion failed")
    return bech32m_encode(hrp, [version] + prog)
