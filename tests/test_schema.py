from bip_gate.schema import (
    Claim,
    ClaimArtifacts,
    CheckResult,
    RouterAnswer,
    RouterPayload,
    Verdict,
)


def test_claim_roundtrip():
    claim = Claim(
        summary="PSBT sends to silent payment address",
        artifacts=ClaimArtifacts(psbt_base64="cHNidP8BAQ=="),
        asserted_bips=[375],
        claimed_complete=False,
    )
    data = claim.model_dump()
    assert Claim.model_validate(data).asserted_bips == [375]


def test_verdict_aggregate_fail_wins():
    router = RouterPayload(
        backend="mock",
        answers={
            "primary_lane": RouterAnswer(type="choice", choice="sp_send_375", confidence=0.9)
        },
    )
    checks = [
        CheckResult(lane="psbt_370", status="not_implemented", evidence="todo"),
        CheckResult(lane="sp_send_375", status="fail", evidence="bad"),
    ]
    v = Verdict.from_checks(lanes_fired=["psbt_370", "sp_send_375"], router=router, checks=checks)
    assert v.verdict == "fail"


def test_verdict_not_implemented_when_only_stubs():
    router = RouterPayload(backend="mock", answers={})
    checks = [
        CheckResult(lane="sp_352", status="not_implemented", evidence="todo"),
    ]
    v = Verdict.from_checks(lanes_fired=["sp_352"], router=router, checks=checks)
    assert v.verdict == "not_implemented"


def test_verdict_pass():
    router = RouterPayload(backend="mock", answers={})
    checks = [CheckResult(lane="sp_send_375", status="pass", evidence="ok")]
    v = Verdict.from_checks(lanes_fired=["sp_send_375"], router=router, checks=checks)
    assert v.verdict == "pass"
