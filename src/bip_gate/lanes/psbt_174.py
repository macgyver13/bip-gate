"""Lane: BIP174 PSBTv0 (stub)."""

from __future__ import annotations

from typing import Any

from bip_gate.lanes.base import Lane, LaneMeta
from bip_gate.schema import CheckResult


class Psbt174Lane(Lane):
    meta = LaneMeta(
        id="psbt_174",
        bip=174,
        title="PSBTv0",
        dependencies=[],
        status="stub",
    )

    def check(self, claim: Any) -> CheckResult:
        # TODO: validate BIP174 map structure + required global unsigned tx
        return self.stub_result(
            refs=["https://github.com/bitcoin/bips/blob/master/bip-0174.mediawiki"],
        )
