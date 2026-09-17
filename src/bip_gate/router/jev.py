"""Optional Jev (TypeSafe System One) router backend.

Requires the ``[jev]`` extra (``typesafe-sdk``) and ``TYPESAFE_API_KEY``.
Falls back to a clear error if the SDK is missing.
"""

from __future__ import annotations

import hashlib
import os
from typing import Any

from bip_gate.router.base import Router, RouterAnswer, RouterResult

try:
    from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

    _HAS_TYPESAFE = True
except ImportError:  # pragma: no cover - exercised when extra not installed
    Choice = Noul = Score = TypeSafeClient = None  # type: ignore[misc, assignment]
    _HAS_TYPESAFE = False

_MERGE_RISK_LEVELS = ["low", "medium", "high", "critical"]


def _digest(value: str | None) -> str | None:
    if not value:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _claim_state(claim: Any) -> dict[str, Any]:
    artifacts = getattr(claim, "artifacts", None)
    return {
        "summary": getattr(claim, "summary", "") or "",
        "asserted_bips": list(getattr(claim, "asserted_bips", None) or []),
        "claimed_complete": bool(getattr(claim, "claimed_complete", False)),
        "artifact_digests": {
            "psbt_base64": _digest(
                getattr(artifacts, "psbt_base64", None) if artifacts else None
            ),
            "psbt_hex": _digest(
                getattr(artifacts, "psbt_hex", None) if artifacts else None
            ),
            "descriptor": _digest(
                getattr(artifacts, "descriptor", None) if artifacts else None
            ),
        },
        "has_psbt_artifact": bool(
            artifacts
            and (
                getattr(artifacts, "psbt_base64", None)
                or getattr(artifacts, "psbt_hex", None)
            )
        ),
        "has_descriptor": bool(artifacts and getattr(artifacts, "descriptor", None)),
    }


def _lane_criteria(lane_ids: list[str]) -> dict[str, str | None]:
    descriptions = {
        "psbt_174": "Legacy PSBTv0 structure and roles (BIP174)",
        "psbt_370": "PSBTv2 structure, counts, and flags (BIP370)",
        "sp_352": "Silent Payments protocol math (BIP352)",
        "sp_send_375": "Sending silent payments with PSBTs (BIP375)",
        "sp_spend_376": "Spending silent payment outputs with PSBTs (BIP376)",
        "sp_desc_392": "Silent payment output descriptors (BIP392)",
    }
    criteria: dict[str, str | None] = {
        lid: descriptions.get(lid, f"Registered lane {lid}") for lid in lane_ids
    }
    criteria["other"] = "None of the registered lanes / unclear"
    return criteria


def _score_to_level(score_answer: Any) -> str:
    """Map a TypeSafe Score answer to a named merge_risk level."""
    legend = getattr(score_answer, "legend", None) or {}
    probs = getattr(score_answer, "probabilities", None) or {}
    if probs and legend:
        # Prefer the mode of the calibrated distribution
        best_idx = max(probs, key=lambda k: probs[k])
        label = legend.get(best_idx) or legend.get(int(best_idx))
        if isinstance(label, str) and label in _MERGE_RISK_LEVELS:
            return label
    raw = getattr(score_answer, "score", None)
    if isinstance(raw, (int, float)) and legend:
        idx = int(round(raw))
        label = legend.get(idx)
        if isinstance(label, str) and label in _MERGE_RISK_LEVELS:
            return label
    if isinstance(raw, str) and raw in _MERGE_RISK_LEVELS:
        return raw
    return "medium"


class JevRouter(Router):
    """Route via TypeSafe / Jev typed decisions when available."""

    backend_name = "jev"

    def route(self, claim: Any, lane_ids: list[str]) -> RouterResult:
        if not _HAS_TYPESAFE:
            raise RuntimeError(
                "Jev backend requested (BIP_GATE_ROUTER=jev) but typesafe-sdk "
                "is not installed. Install with: pip install 'bip-gate[jev]'"
            )
        api_key = os.environ.get("TYPESAFE_API_KEY")
        if not api_key:
            raise RuntimeError(
                "BIP_GATE_ROUTER=jev requires TYPESAFE_API_KEY in the environment"
            )

        state = _claim_state(claim)
        criteria = _lane_criteria(lane_ids)
        model = os.environ.get("TYPESAFE_DEFAULT_MODEL", "jev-latest")

        assert Choice is not None and Noul is not None and Score is not None
        assert TypeSafeClient is not None

        questions = {
            "primary_lane": Choice(
                instructions=(
                    "Which BIP correctness lane should primarily handle this claim? "
                    "Prefer the most specific matching lane."
                ),
                criteria=criteria,
            ),
            "is_silent_payments_related": Noul(
                instructions=(
                    "Is this claim about Silent Payments "
                    "(BIP352, BIP375, BIP376, or BIP392)?"
                ),
            ),
            "touches_psbt": Noul(
                instructions=(
                    "Does this claim involve a PSBT, PSBT fields, or PSBT roles "
                    "(BIP174/BIP370/BIP375/BIP376)?"
                ),
            ),
            "merge_risk": Score(
                instructions=(
                    "How risky would merging agent-written code for this claim be "
                    "without human review?"
                ),
                criteria=_MERGE_RISK_LEVELS,
            ),
        }

        with TypeSafeClient() as client:
            response = client.system_one(
                state=state,
                questions=questions,
                model=model,
            )

        choice = response.choices["primary_lane"]
        sp = response.nouls["is_silent_payments_related"]
        psbt = response.nouls["touches_psbt"]
        risk = response.scores["merge_risk"]

        primary = choice.choice
        if primary not in lane_ids and primary != "other":
            primary = "other"

        answers = {
            "primary_lane": RouterAnswer(
                type="choice",
                choice=primary,
                confidence=float(getattr(choice, "confidence", 0.0) or 0.0),
            ),
            "is_silent_payments_related": RouterAnswer(
                type="noul",
                probability=float(sp.noul),
                confidence=1.0,
            ),
            "touches_psbt": RouterAnswer(
                type="noul",
                probability=float(psbt.noul),
                confidence=1.0,
            ),
            "merge_risk": RouterAnswer(
                type="score",
                score=_score_to_level(risk),
                confidence=float(getattr(risk, "confidence", 0.0) or 0.0),
            ),
        }
        return RouterResult(backend=self.backend_name, answers=answers)
