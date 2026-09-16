from bip_gate.lanes.registry import (
    dependency_closure,
    get_lane,
    list_lanes,
    resolve_lanes,
)
from bip_gate.router.base import RouterAnswer, RouterResult
from bip_gate.schema import Claim


def test_six_bip_lanes_registered():
    ids = {lane.meta.id for lane in list_lanes()}
    expected = {
        "psbt_174",
        "psbt_370",
        "sp_352",
        "sp_send_375",
        "sp_spend_376",
        "sp_desc_392",
    }
    assert expected <= ids
    assert len(ids) == 6


def test_dependency_closure_sp_send_375():
    closed = dependency_closure(["sp_send_375"])
    assert closed.index("psbt_174") < closed.index("psbt_370")
    assert "sp_352" in closed
    assert closed[-1] == "sp_send_375"


def test_resolve_from_asserted_bips():
    claim = Claim(summary="x", asserted_bips=[375])
    routed = RouterResult(
        backend="mock",
        answers={
            "primary_lane": RouterAnswer(type="choice", choice="sp_send_375", confidence=0.9),
            "is_silent_payments_related": RouterAnswer(
                type="noul", probability=0.9, confidence=0.8
            ),
            "touches_psbt": RouterAnswer(type="noul", probability=0.9, confidence=0.8),
            "merge_risk": RouterAnswer(type="score", score="high", confidence=0.7),
        },
    )
    lanes = resolve_lanes(routed, claim)
    ids = [lane.meta.id for lane in lanes]
    assert "sp_send_375" in ids
    assert "psbt_370" in ids
    assert "sp_352" in ids


def test_get_lane():
    assert get_lane("sp_send_375") is not None
    assert get_lane("nope") is None
