"""Lane: BIP352 Silent Payments protocol (partial structural checker)."""

from __future__ import annotations

import re
from typing import Any

from bip_gate.lanes.base import Lane, LaneMeta
from bip_gate.lanes.sp_address import (
    SpAddressError,
    SilentPaymentAddress,
    decode_silent_payment_address,
)
from bip_gate.schema import CheckResult

BIP352_REFS = [
    "https://github.com/bitcoin/bips/blob/master/bip-0352.mediawiki",
    "https://github.com/bitcoin/bips/blob/master/bip-0352.mediawiki#address-encoding",
    "https://github.com/bitcoin/bips/blob/master/bip-0350.mediawiki",
    "BIP352 vectors: bip-0352/send_and_receive_test_vectors.json",
]

_SP_ADDR_RE = re.compile(r"\b(?:sp|tsp)1[0-9a-zA-Z]{20,}\b")

_PROTOCOL_MATH_RE = re.compile(
    r"\b("
    r"ecdh|"
    r"shared\s+secret|"
    r"output\s+derivation|"
    r"labeled\s+address\s+generation|"
    r"tweak(?:ed|ing)?\s+output|"
    r"scan(?:ning)?\s+outputs?"
    r")\b",
    re.IGNORECASE,
)


def _extra(claim: Any) -> dict[str, Any]:
    artifacts = getattr(claim, "artifacts", None)
    if artifacts is None:
        return {}
    extra = getattr(artifacts, "extra", None)
    return dict(extra) if isinstance(extra, dict) else {}


def _collect_addresses(claim: Any) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()

    def add(value: Any) -> None:
        if not isinstance(value, str):
            return
        text = value.strip()
        if not text:
            return
        key = text.lower()
        if key in seen:
            return
        seen.add(key)
        found.append(text)

    extra = _extra(claim)
    add(extra.get("sp_address"))
    addresses = extra.get("addresses")
    if isinstance(addresses, list):
        for item in addresses:
            add(item)
    elif isinstance(addresses, str):
        add(addresses)

    summary = getattr(claim, "summary", None) or ""
    for match in _SP_ADDR_RE.findall(str(summary)):
        add(match)

    return found


def _parse_hex_pubkey(value: Any, label: str) -> bytes | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise SpAddressError(f"{label} must be hex string")
    text = value.strip().lower()
    if text.startswith("0x"):
        text = text[2:]
    try:
        raw = bytes.fromhex(text)
    except ValueError as exc:
        raise SpAddressError(f"{label} is not valid hex") from exc
    if len(raw) != 33:
        raise SpAddressError(f"{label} length {len(raw)} != 33")
    if raw[0] not in (0x02, 0x03):
        raise SpAddressError(f"{label} is not a compressed pubkey")
    return raw


def _asserts_protocol_math(claim: Any, extra: dict[str, Any]) -> bool:
    if bool(getattr(claim, "claimed_complete", False)):
        return True
    if extra.get("asserts_protocol_math"):
        return True
    summary = str(getattr(claim, "summary", None) or "")
    return bool(_PROTOCOL_MATH_RE.search(summary))


class Sp352Lane(Lane):
    meta = LaneMeta(
        id="sp_352",
        bip=352,
        title="Silent Payments",
        dependencies=[],
        status="partial",
    )

    def check(self, claim: Any) -> CheckResult:
        extra = _extra(claim)
        addresses = _collect_addresses(claim)

        try:
            scan_key = _parse_hex_pubkey(extra.get("scan_pub_key"), "scan_pub_key")
            spend_key = _parse_hex_pubkey(extra.get("spend_pub_key"), "spend_pub_key")
        except SpAddressError as exc:
            return CheckResult(
                lane=self.meta.id,
                status="fail",
                evidence=f"Invalid pubkey artifact (fail closed): {exc}",
                refs=BIP352_REFS,
            )

        has_both_keys = scan_key is not None and spend_key is not None
        has_any_key = scan_key is not None or spend_key is not None

        if (scan_key is None) ^ (spend_key is None):
            return CheckResult(
                lane=self.meta.id,
                status="fail",
                evidence=(
                    "scan_pub_key and spend_pub_key must both be provided "
                    "to verify against a silent payment address payload"
                ),
                refs=BIP352_REFS,
            )

        if not addresses and not has_any_key:
            return CheckResult(
                lane=self.meta.id,
                status="need_human",
                evidence=(
                    "No silent payment address or scan/spend pubkeys on claim; "
                    "cannot run BIP352 structural checks"
                ),
                refs=BIP352_REFS,
            )

        if not addresses and has_any_key:
            return CheckResult(
                lane=self.meta.id,
                status="need_human",
                evidence=(
                    "scan/spend pubkeys present but no silent payment address to "
                    "structurally verify; ECDH/output-derivation crypto not wired"
                ),
                refs=BIP352_REFS,
            )

        decoded: list[SilentPaymentAddress] = []
        findings: list[str] = []
        for addr in addresses:
            try:
                sp = decode_silent_payment_address(addr)
            except SpAddressError as exc:
                shown = addr if len(addr) <= 48 else f"{addr[:24]}…{addr[-12:]}"
                return CheckResult(
                    lane=self.meta.id,
                    status="fail",
                    evidence=(
                        f"Invalid silent payment address (fail closed): {exc}; "
                        f"address={shown}"
                    ),
                    refs=BIP352_REFS,
                )
            decoded.append(sp)
            findings.append(
                f"ok {sp.hrp} v{sp.version} "
                f"B_scan={sp.scan_pubkey.hex()[:16]}… "
                f"B_m={sp.spend_pubkey.hex()[:16]}…"
            )

        if has_both_keys:
            assert scan_key is not None and spend_key is not None
            matched = any(
                sp.scan_pubkey == scan_key and sp.spend_pubkey == spend_key
                for sp in decoded
            )
            if not matched:
                return CheckResult(
                    lane=self.meta.id,
                    status="fail",
                    evidence=(
                        "scan_pub_key/spend_pub_key do not match decoded "
                        "66-byte silent payment address payload. "
                        + "; ".join(findings)
                    ),
                    refs=BIP352_REFS,
                )
            findings.append("scan_pub_key/spend_pub_key match address payload")

        if _asserts_protocol_math(claim, extra):
            return CheckResult(
                lane=self.meta.id,
                status="need_human",
                evidence=(
                    "Claim asserts ECDH / shared-secret / output-derivation "
                    "(protocol math) complete, but secp256k1 ECDH and tweak "
                    "verification are not wired in this lane — structural address "
                    "encoding alone is insufficient. "
                    + "; ".join(findings)
                ),
                refs=BIP352_REFS,
            )

        return CheckResult(
            lane=self.meta.id,
            status="pass",
            evidence=(
                "Structural BIP352 silent payment address checks passed "
                "(Bech32m HRP/version/66-byte payload/compressed pubkeys). "
                "Note: ECDH/shared-secret/output-derivation crypto is not wired. "
                + "; ".join(findings)
            ),
            refs=BIP352_REFS,
        )
