"""Lane plugin base types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from bip_gate.schema import CheckResult, CheckStatus


@dataclass
class LaneMeta:
    id: str
    bip: int | None
    title: str
    dependencies: list[str] = field(default_factory=list)
    status: str = "stub"  # stub | partial | implemented


class Lane(ABC):
    """A BIP lane: metadata + deterministic checker."""

    meta: LaneMeta

    @abstractmethod
    def check(self, claim: Any) -> CheckResult:
        """Run structural / oracle checks for this lane."""

    def stub_result(
        self,
        *,
        status: CheckStatus = "not_implemented",
        evidence: str | None = None,
        refs: list[str] | None = None,
    ) -> CheckResult:
        bip = self.meta.bip
        bip_ref = f"BIP{bip}" if bip else "generic"
        return CheckResult(
            lane=self.meta.id,
            status=status,
            evidence=evidence
            or (
                f"TODO: implement deterministic checker for {self.meta.id} "
                f"({bip_ref} — {self.meta.title})"
            ),
            refs=refs or ([f"https://github.com/bitcoin/bips/blob/master/bip-{bip:04d}.mediawiki"] if bip else []),
        )
