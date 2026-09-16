from bip_gate.lanes.sp_send_375 import SpSend375Lane
from bip_gate.schema import Claim, ClaimArtifacts
from tests.fixtures.psbt_helpers import (
    as_b64,
    as_hex,
    make_psbt_v2,
    sp_info_value,
)


lane = SpSend375Lane()


def test_incomplete_sp_send_need_human():
    psbt = make_psbt_v2(
        outputs=[
            {"sp_info": sp_info_value(), "script": None},
        ]
    )
    claim = Claim(
        summary="PSBT sends to silent payment address",
        artifacts=ClaimArtifacts(psbt_base64=as_b64(psbt)),
        asserted_bips=[375],
        claimed_complete=False,
    )
    result = lane.check(claim)
    assert result.status == "need_human"
    assert "incomplete" in result.evidence.lower() or "not yet computed" in result.evidence.lower()


def test_incomplete_but_claimed_complete_fails():
    psbt = make_psbt_v2(
        outputs=[
            {"sp_info": sp_info_value(), "script": None},
        ]
    )
    claim = Claim(
        summary="complete SP send",
        artifacts=ClaimArtifacts(psbt_hex=as_hex(psbt)),
        asserted_bips=[375],
        claimed_complete=True,
    )
    result = lane.check(claim)
    assert result.status == "fail"


def test_sp_with_script_structural_pass():
    script = bytes([0x51, 0x20]) + b"\x11" * 32  # fake OP_1 OP_PUSH32
    psbt = make_psbt_v2(
        outputs=[
            {"sp_info": sp_info_value(), "script": script},
        ]
    )
    claim = Claim(
        summary="SP send with computed script",
        artifacts=ClaimArtifacts(psbt_base64=as_b64(psbt)),
        asserted_bips=[375],
        claimed_complete=True,
    )
    result = lane.check(claim)
    assert result.status == "pass"
    assert "0x09" in " ".join(result.refs) or "SP_V0_INFO" in " ".join(result.refs)


def test_missing_script_and_sp_info_fails():
    psbt = make_psbt_v2(outputs=[{}])
    claim = Claim(
        summary="broken output",
        artifacts=ClaimArtifacts(psbt_base64=as_b64(psbt)),
        asserted_bips=[375],
    )
    result = lane.check(claim)
    assert result.status == "fail"
    assert "missing both" in result.evidence.lower()


def test_bad_sp_info_length_fails():
    psbt = make_psbt_v2(outputs=[{"sp_info": b"\x00" * 10}])
    claim = Claim(
        summary="bad info",
        artifacts=ClaimArtifacts(psbt_base64=as_b64(psbt)),
        asserted_bips=[375],
    )
    result = lane.check(claim)
    assert result.status == "fail"
    assert "66" in result.evidence


def test_label_without_info_fails():
    psbt = make_psbt_v2(
        outputs=[{"sp_label": (0).to_bytes(4, "little"), "script": b"\x51"}]
    )
    claim = Claim(
        summary="label only",
        artifacts=ClaimArtifacts(psbt_base64=as_b64(psbt)),
        asserted_bips=[375],
    )
    result = lane.check(claim)
    assert result.status == "fail"


def test_non_psbt_fails():
    claim = Claim(
        summary="not a psbt",
        artifacts=ClaimArtifacts(psbt_base64="aGVsbG8="),
        asserted_bips=[375],
    )
    result = lane.check(claim)
    assert result.status == "fail"


def test_no_artifact_need_human():
    claim = Claim(summary="no blob", asserted_bips=[375])
    result = lane.check(claim)
    assert result.status == "need_human"
