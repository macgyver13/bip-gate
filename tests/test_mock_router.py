from bip_gate.lanes.registry import list_lanes
from bip_gate.router.mock import MockRouter
from bip_gate.schema import Claim, ClaimArtifacts


def test_mock_routes_asserted_bip_375():
    router = MockRouter()
    lane_ids = [lane.meta.id for lane in list_lanes()]
    claim = Claim(
        summary="send to SP",
        asserted_bips=[375],
        artifacts=ClaimArtifacts(),
    )
    result = router.route(claim, lane_ids)
    assert result.backend == "mock"
    assert result.answers["primary_lane"].choice == "sp_send_375"
    assert result.answers["is_silent_payments_related"].probability >= 0.5
    assert result.answers["touches_psbt"].type == "noul"
    assert result.answers["merge_risk"].score in {"low", "medium", "high", "critical"}


def test_mock_detects_psbt_artifact():
    router = MockRouter()
    lane_ids = [lane.meta.id for lane in list_lanes()]
    claim = Claim(
        summary="unsigned tx",
        artifacts=ClaimArtifacts(psbt_hex="70736274ff"),
        asserted_bips=[370],
    )
    result = router.route(claim, lane_ids)
    assert result.answers["touches_psbt"].probability >= 0.5
    assert result.answers["primary_lane"].choice == "psbt_370"
