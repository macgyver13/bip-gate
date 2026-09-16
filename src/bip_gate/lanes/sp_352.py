"""Lane: BIP352 Silent Payments protocol (stub)."""

from __future__ import annotations

from typing import Any

from bip_gate.lanes.base import Lane, LaneMeta
from bip_gate.schema import CheckResult


class Sp352Lane(Lane):
    meta = LaneMeta(
        id="sp_352",
        bip=352,
        title="Silent Payments",
        dependencies=[],
        status="stub",
    )

    def check(self, claim: Any) -> CheckResult:
        # TODO: protocol math hooks (ECDH, output derivation) against BIP352 vectors
        return self.stub_result(
            refs=["https://github.com/bitcoin/bips/blob/master/bip-0352.mediawiki"],
        )
