"""Lane registry and dependency closure."""

from __future__ import annotations

from typing import Any, Iterable

from bip_gate.lanes.base import Lane
from bip_gate.lanes import (
    psbt_174,
    psbt_370,
    sp_352,
    sp_send_375,
    sp_spend_376,
    sp_desc_392,
)
from bip_gate.router.base import RouterResult

# BIP number → lane id
BIP_TO_LANE: dict[int, str] = {
    174: "psbt_174",
    370: "psbt_370",
    352: "sp_352",
    375: "sp_send_375",
    376: "sp_spend_376",
    392: "sp_desc_392",
}


def _build_registry() -> dict[str, Lane]:
    lanes: list[Lane] = [
        psbt_174.Psbt174Lane(),
        psbt_370.Psbt370Lane(),
        sp_352.Sp352Lane(),
        sp_send_375.SpSend375Lane(),
        sp_spend_376.SpSpend376Lane(),
        sp_desc_392.SpDesc392Lane(),
    ]
    return {lane.meta.id: lane for lane in lanes}


_REGISTRY: dict[str, Lane] | None = None


def registry() -> dict[str, Lane]:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = _build_registry()
    return _REGISTRY


def list_lanes() -> list[Lane]:
    return list(registry().values())


def get_lane(lane_id: str) -> Lane | None:
    return registry().get(lane_id)


def dependency_closure(lane_ids: Iterable[str]) -> list[str]:
    """Return lane ids plus transitive dependencies (stable order)."""
    reg = registry()
    seen: set[str] = set()
    ordered: list[str] = []

    def visit(lid: str) -> None:
        if lid in seen or lid not in reg:
            return
        seen.add(lid)
        for dep in reg[lid].meta.dependencies:
            visit(dep)
        ordered.append(lid)

    for lid in lane_ids:
        visit(lid)
    return ordered


def lanes_from_router(
    router_result: RouterResult,
    claim: Any,
) -> list[str]:
    """Map router answers + asserted BIPs → lane set with dependency closure."""
    selected: set[str] = set()
    answers = router_result.answers

    primary = answers.get("primary_lane")
    if primary and primary.choice and primary.choice != "other":
        selected.add(primary.choice)

    asserted = list(getattr(claim, "asserted_bips", None) or [])
    for bip in asserted:
        lid = BIP_TO_LANE.get(bip)
        if lid:
            selected.add(lid)

    is_sp = answers.get("is_silent_payments_related")
    if is_sp and (is_sp.probability or 0) >= 0.5:
        # Soft bias: if SP-related but no primary, include protocol lane
        if not selected:
            selected.add("sp_352")

    touches = answers.get("touches_psbt")
    if touches and (touches.probability or 0) >= 0.5 and not any(
        x.startswith("psbt_") or x.startswith("sp_send") for x in selected
    ):
        selected.add("psbt_370")

    if not selected:
        # Catch-all: need_human path via a stub generic pointer — use psbt_174
        # as the least-specific registered lane when nothing matches; CLI also
        # documents how to add a lane in CONTRIBUTING.
        return []

    return dependency_closure(selected)


def resolve_lanes(router_result: RouterResult, claim: Any) -> list[Lane]:
    ids = lanes_from_router(router_result, claim)
    reg = registry()
    return [reg[i] for i in ids if i in reg]
