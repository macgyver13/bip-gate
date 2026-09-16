"""Lane: BIP376 Spending Silent Payments (stub)."""

from __future__ import annotations

from typing import Any

from bip_gate.lanes.base import Lane, LaneMeta
from bip_gate.schema import CheckResult


class SpSpend376Lane(Lane):
    meta = LaneMeta(
        id="sp_spend_376",
        bip=376,
        title="Spending Silent Payments",
        dependencies=["sp_352"],
        status="stub",
    )

    def check(self, claim: Any) -> CheckResult:
        # TODO: spend-path structural checks per BIP376
        return self.stub_result(
            refs=["https://github.com/bitcoin/bips/blob/master/bip-0376.mediawiki"],
        )
