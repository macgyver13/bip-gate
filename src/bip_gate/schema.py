"""Claim and Verdict models for machine-readable gate results."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class VerdictStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    NEED_HUMAN = "need_human"
    NOT_IMPLEMENTED = "not_implemented"


CheckStatus = Literal["pass", "fail", "need_human", "not_implemented"]


class ClaimArtifacts(BaseModel):
    """Optional artifacts attached to a correctness claim."""

    psbt_base64: str | None = None
    psbt_hex: str | None = None
    descriptor: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class Claim(BaseModel):
    """A developer/agent claim that bip-gate will route and check."""

    summary: str = ""
    artifacts: ClaimArtifacts = Field(default_factory=ClaimArtifacts)
    asserted_bips: list[int] = Field(default_factory=list)
    claimed_complete: bool = False


class RouterAnswer(BaseModel):
    """One typed router answer (Choice / Noul / Score)."""

    type: Literal["choice", "noul", "score"]
    choice: str | None = None
    probability: float | None = None
    score: str | None = None
    confidence: float = 0.0


class RouterPayload(BaseModel):
    backend: str
    answers: dict[str, RouterAnswer] = Field(default_factory=dict)


class CheckResult(BaseModel):
    lane: str
    status: CheckStatus
    evidence: str = ""
    refs: list[str] = Field(default_factory=list)


class Verdict(BaseModel):
    """Machine verdict for CI / agent loops."""

    verdict: CheckStatus
    lanes_fired: list[str] = Field(default_factory=list)
    router: RouterPayload
    checks: list[CheckResult] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)

    @classmethod
    def from_checks(
        cls,
        *,
        lanes_fired: list[str],
        router: RouterPayload,
        checks: list[CheckResult],
        blockers: list[str] | None = None,
    ) -> Verdict:
        """Aggregate per-lane checks into a single verdict (fail-closed)."""
        blockers = list(blockers or [])
        statuses = [c.status for c in checks]
        if not statuses:
            overall: CheckStatus = "need_human"
            blockers.append("no lanes fired")
        elif any(s == "fail" for s in statuses):
            overall = "fail"
        elif any(s == "need_human" for s in statuses):
            overall = "need_human"
        elif any(s == "not_implemented" for s in statuses):
            overall = "not_implemented"
        elif all(s == "pass" for s in statuses):
            overall = "pass"
        else:
            overall = "need_human"
        return cls(
            verdict=overall,
            lanes_fired=lanes_fired,
            router=router,
            checks=checks,
            blockers=blockers,
        )
