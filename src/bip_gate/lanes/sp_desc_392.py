"""Lane: BIP392 Silent Payment descriptors (stub)."""

from __future__ import annotations

from typing import Any

from bip_gate.lanes.base import Lane, LaneMeta
from bip_gate.schema import CheckResult


class SpDesc392Lane(Lane):
    meta = LaneMeta(
        id="sp_desc_392",
        bip=392,
        title="Silent Payment descriptors",
        dependencies=["sp_352"],
        status="stub",
    )

    def check(self, claim: Any) -> CheckResult:
        # TODO: descriptor grammar checks per BIP392
        return self.stub_result(
            refs=["https://github.com/bitcoin/bips/blob/master/bip-0392.mediawiki"],
        )
