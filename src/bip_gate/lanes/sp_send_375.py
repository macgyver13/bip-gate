"""Lane: BIP375 Sending Silent Payments with PSBTs (structural checker)."""

from __future__ import annotations

from typing import Any

from bip_gate.lanes.base import Lane, LaneMeta
from bip_gate.lanes.psbt_parse import (
    PSBT_OUT_SCRIPT,
    PSBT_OUT_SP_V0_INFO,
    PSBT_OUT_SP_V0_LABEL,
    PsbtParseError,
    looks_like_psbt,
    parse_psbt,
)
from bip_gate.schema import CheckResult

BIP375_REFS = [
    "https://github.com/bitcoin/bips/blob/master/bip-0375.mediawiki",
    "BIP375: PSBT_OUT_SP_V0_INFO=0x09, PSBT_OUT_SP_V0_LABEL=0x0a, PSBT_OUT_SCRIPT=0x04 (BIP370)",
    "BIP375: each output must have PSBT_OUT_SCRIPT and/or PSBT_OUT_SP_V0_INFO",
]


class SpSend375Lane(Lane):
    meta = LaneMeta(
        id="sp_send_375",
        bip=375,
        title="Sending Silent Payments with PSBTs",
        dependencies=["psbt_370", "sp_352"],
        status="partial",
    )

    def check(self, claim: Any) -> CheckResult:
        artifacts = getattr(claim, "artifacts", None)
        raw = None
        if artifacts is not None:
            raw = getattr(artifacts, "psbt_base64", None) or getattr(
                artifacts, "psbt_hex", None
            )
        claimed_complete = bool(getattr(claim, "claimed_complete", False))

        if not raw or not str(raw).strip():
            return CheckResult(
                lane=self.meta.id,
                status="need_human",
                evidence="No PSBT artifact on claim; cannot run BIP375 structural checks",
                refs=BIP375_REFS,
            )

        if not looks_like_psbt(raw):
            return CheckResult(
                lane=self.meta.id,
                status="fail",
                evidence="Artifact does not decode as PSBT (missing magic or bad encoding)",
                refs=BIP375_REFS,
            )

        try:
            parsed = parse_psbt(raw)
        except PsbtParseError as exc:
            return CheckResult(
                lane=self.meta.id,
                status="fail",
                evidence=f"PSBT parse error (fail closed): {exc}",
                refs=BIP375_REFS,
            )

        findings: list[str] = []
        sp_outputs = 0
        incomplete_sp = 0
        missing_both = 0
        label_without_info = 0

        for idx, out in enumerate(parsed.outputs):
            has_script = out.has_type(PSBT_OUT_SCRIPT)
            has_sp = out.has_type(PSBT_OUT_SP_V0_INFO)
            has_label = out.has_type(PSBT_OUT_SP_V0_LABEL)

            if has_label and not has_sp:
                label_without_info += 1
                findings.append(
                    f"output[{idx}]: PSBT_OUT_SP_V0_LABEL without PSBT_OUT_SP_V0_INFO"
                )

            if not has_script and not has_sp:
                missing_both += 1
                findings.append(
                    f"output[{idx}]: missing both PSBT_OUT_SCRIPT and PSBT_OUT_SP_V0_INFO"
                )
                continue

            if has_sp:
                sp_outputs += 1
                # Validate SP_V0_INFO value length: 33-byte scan + 33-byte spend = 66
                for val in out.values_for_type(PSBT_OUT_SP_V0_INFO):
                    if len(val) != 66:
                        findings.append(
                            f"output[{idx}]: PSBT_OUT_SP_V0_INFO length {len(val)} != 66"
                        )
                if not has_script:
                    incomplete_sp += 1
                    findings.append(
                        f"output[{idx}]: SP info present, script not yet computed "
                        "(in-progress silent payment send)"
                    )

        # Heuristic note if global SP keys present
        gtypes = parsed.global_map.key_types()
        if 0x07 in gtypes or 0x08 in gtypes:
            findings.append(
                "global map contains BIP375 ECDH/DLEQ fields "
                "(PSBT_GLOBAL_SP_ECDH_SHARE=0x07 / PSBT_GLOBAL_SP_DLEQ=0x08)"
            )

        version_note = (
            f"psbt_version={parsed.psbt_version}"
            if parsed.psbt_version is not None
            else "psbt_version=absent(v0-or-implicit)"
        )
        findings.insert(
            0,
            f"{version_note}; outputs={len(parsed.outputs)}; "
            f"sp_outputs={sp_outputs}; incomplete_sp={incomplete_sp}",
        )

        if missing_both or label_without_info:
            return CheckResult(
                lane=self.meta.id,
                status="fail",
                evidence="; ".join(findings),
                refs=BIP375_REFS,
            )

        # Incorrect SP_V0_INFO length is a structural fail
        if any("length" in f and "PSBT_OUT_SP_V0_INFO" in f for f in findings):
            return CheckResult(
                lane=self.meta.id,
                status="fail",
                evidence="; ".join(findings),
                refs=BIP375_REFS,
            )

        if incomplete_sp:
            if claimed_complete:
                return CheckResult(
                    lane=self.meta.id,
                    status="fail",
                    evidence=(
                        "Claim marked complete but silent-payment outputs lack "
                        f"PSBT_OUT_SCRIPT ({incomplete_sp} incomplete). "
                        + "; ".join(findings)
                    ),
                    refs=BIP375_REFS,
                )
            return CheckResult(
                lane=self.meta.id,
                status="need_human",
                evidence=(
                    "Incomplete SP send (info without script). Structural OK so far; "
                    "crypto/DLEQ verification not wired — human or deeper oracle needed. "
                    + "; ".join(findings)
                ),
                refs=BIP375_REFS,
            )

        if sp_outputs == 0:
            # Valid non-SP PSBT under BIP375 presence rules, but lane is SP-send focused
            return CheckResult(
                lane=self.meta.id,
                status="need_human",
                evidence=(
                    "No PSBT_OUT_SP_V0_INFO outputs found; not an SP send under BIP375. "
                    + "; ".join(findings)
                ),
                refs=BIP375_REFS,
            )

        # SP outputs all have scripts — structural pass; crypto still not verified
        return CheckResult(
            lane=self.meta.id,
            status="pass",
            evidence=(
                "Structural BIP375 output rules satisfied "
                "(SP info ± script presence). "
                "Note: ECDH/DLEQ/output-script crypto verification is not wired "
                "(would be need_human if required). "
                + "; ".join(findings)
            ),
            refs=BIP375_REFS,
        )
