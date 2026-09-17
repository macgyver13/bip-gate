"""Jev router unit tests (mocked SDK — no live API key required)."""

from __future__ import annotations

from types import SimpleNamespace

import bip_gate.router.jev as jev_mod
from bip_gate.schema import Claim, ClaimArtifacts


class _FakeChoice:
    def __init__(self, choice: str, confidence: float = 0.9):
        self.choice = choice
        self.confidence = confidence
        self.probabilities = {choice: 1.0}


class _FakeNoul:
    def __init__(self, noul: float):
        self.noul = noul


class _FakeScore:
    def __init__(self, score: float = 2.0, confidence: float = 0.5):
        self.score = score
        self.confidence = confidence
        self.legend = {0: "low", 1: "medium", 2: "high", 3: "critical"}
        self.probabilities = {0: 0.0, 1: 0.1, 2: 0.7, 3: 0.2}


class _FakeResponse:
    def __init__(self):
        self.choices = {"primary_lane": _FakeChoice("sp_send_375", 0.99)}
        self.nouls = {
            "is_silent_payments_related": _FakeNoul(0.9),
            "touches_psbt": _FakeNoul(0.95),
        }
        self.scores = {"merge_risk": _FakeScore()}


class _FakeClient:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def system_one(self, **kwargs):
        assert "state" in kwargs and "questions" in kwargs
        return _FakeResponse()


def test_jev_router_maps_answers(monkeypatch):
    monkeypatch.setattr(jev_mod, "_HAS_TYPESAFE", True)
    monkeypatch.setattr(jev_mod, "TypeSafeClient", _FakeClient)
    monkeypatch.setattr(jev_mod, "Choice", object)
    monkeypatch.setattr(jev_mod, "Noul", object)
    monkeypatch.setattr(jev_mod, "Score", object)
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")

    # Choice/Noul/Score are constructed inside route — stub callables
    class _Q:
        def __init__(self, *a, **k):
            pass

    monkeypatch.setattr(jev_mod, "Choice", _Q)
    monkeypatch.setattr(jev_mod, "Noul", _Q)
    monkeypatch.setattr(jev_mod, "Score", _Q)

    router = jev_mod.JevRouter()
    claim = Claim(
        summary="PSBT sends to silent payment",
        asserted_bips=[375],
        artifacts=ClaimArtifacts(psbt_base64="cHNidP8="),
    )
    result = router.route(
        claim,
        [
            "psbt_174",
            "psbt_370",
            "sp_352",
            "sp_send_375",
            "sp_spend_376",
            "sp_desc_392",
        ],
    )
    assert result.backend == "jev"
    assert result.answers["primary_lane"].choice == "sp_send_375"
    assert result.answers["is_silent_payments_related"].probability == 0.9
    assert result.answers["touches_psbt"].probability == 0.95
    assert result.answers["merge_risk"].score == "high"


def test_score_to_level_uses_mode():
    ans = SimpleNamespace(
        score=2.4,
        legend={0: "low", 1: "medium", 2: "high", 3: "critical"},
        probabilities={0: 0.02, 1: 0.06, 2: 0.47, 3: 0.45},
    )
    assert jev_mod._score_to_level(ans) == "high"
