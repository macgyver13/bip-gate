"""Heuristic mock router — default so the community needs no TypeSafe key."""

from __future__ import annotations

from typing import Any

from bip_gate.router.base import Router, RouterAnswer, RouterResult

# BIP number → preferred lane id
_BIP_TO_LANE: dict[int, str] = {
    174: "psbt_174",
    370: "psbt_370",
    352: "sp_352",
    375: "sp_send_375",
    376: "sp_spend_376",
    392: "sp_desc_392",
}

_SP_KEYWORDS = (
    "silent payment",
    "silent_payment",
    "sp_v0",
    "bip375",
    "bip-375",
    "bip352",
    "bip-352",
)
_PSBT_KEYWORDS = ("psbt", "partially signed")


class MockRouter(Router):
    """Keyword / asserted_bips heuristic producing Choice/Noul/Score answers."""

    backend_name = "mock"

    def route(self, claim: Any, lane_ids: list[str]) -> RouterResult:
        summary = (getattr(claim, "summary", None) or "").lower()
        asserted: list[int] = list(getattr(claim, "asserted_bips", None) or [])
        artifacts = getattr(claim, "artifacts", None)
        has_psbt = False
        blob = ""
        if artifacts is not None:
            psbt_b64 = getattr(artifacts, "psbt_base64", None) or ""
            psbt_hex = getattr(artifacts, "psbt_hex", None) or ""
            has_psbt = bool(psbt_b64 or psbt_hex)
            blob = f"{psbt_b64} {psbt_hex}".lower()

        text = f"{summary} {blob}"

        is_sp = any(k in text for k in _SP_KEYWORDS) or any(
            b in (352, 375, 376, 392) for b in asserted
        )
        touches_psbt = (
            has_psbt
            or any(k in text for k in _PSBT_KEYWORDS)
            or any(b in (174, 370, 375) for b in asserted)
        )

        primary = "other"
        for bip in asserted:
            lane = _BIP_TO_LANE.get(bip)
            if lane and lane in lane_ids:
                primary = lane
                break
        if primary == "other":
            if is_sp and "sp_send_375" in lane_ids and (
                375 in asserted or "send" in summary or "375" in summary
            ):
                primary = "sp_send_375"
            elif is_sp and "sp_352" in lane_ids:
                primary = "sp_352"
            elif touches_psbt and "psbt_370" in lane_ids:
                primary = "psbt_370"
            elif touches_psbt and "psbt_174" in lane_ids:
                primary = "psbt_174"

        # merge_risk: SP+PSBT incomplete claims are higher risk
        if is_sp and touches_psbt:
            risk = "high"
        elif is_sp or touches_psbt:
            risk = "medium"
        else:
            risk = "low"

        answers = {
            "primary_lane": RouterAnswer(
                type="choice",
                choice=primary if primary in lane_ids or primary == "other" else "other",
                confidence=0.85 if primary != "other" else 0.4,
            ),
            "is_silent_payments_related": RouterAnswer(
                type="noul",
                probability=0.9 if is_sp else 0.1,
                confidence=0.8,
            ),
            "touches_psbt": RouterAnswer(
                type="noul",
                probability=0.9 if touches_psbt else 0.1,
                confidence=0.8,
            ),
            "merge_risk": RouterAnswer(
                type="score",
                score=risk,
                confidence=0.7,
            ),
        }
        return RouterResult(backend=self.backend_name, answers=answers)
