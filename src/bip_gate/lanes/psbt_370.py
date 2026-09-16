"""Lane: BIP370 PSBTv2 (stub + shared parse hook placeholder)."""

from __future__ import annotations

from typing import Any

from bip_gate.lanes.base import Lane, LaneMeta
from bip_gate.schema import CheckResult


class Psbt370Lane(Lane):
    meta = LaneMeta(
        id="psbt_370",
        bip=370,
        title="PSBTv2",
        dependencies=["psbt_174"],
        status="stub",
    )

    def check(self, claim: Any) -> CheckResult:
        # TODO: shared PSBTv2 parse hook (version, input/output counts, modifiable flags)
        return self.stub_result(
            refs=["https://github.com/bitcoin/bips/blob/master/bip-0370.mediawiki"],
        )
