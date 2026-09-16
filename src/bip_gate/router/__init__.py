"""Router backends: mock (default) and optional Jev."""

from __future__ import annotations

import os

from bip_gate.router.base import Router, RouterAnswer, RouterResult
from bip_gate.router.mock import MockRouter


def get_router() -> Router:
    """Return the configured router backend.

    Controlled by ``BIP_GATE_ROUTER``: ``mock`` (default) or ``jev``.
    """
    backend = os.environ.get("BIP_GATE_ROUTER", "mock").strip().lower()
    if backend == "jev":
        from bip_gate.router.jev import JevRouter

        return JevRouter()
    return MockRouter()


__all__ = [
    "Router",
    "RouterAnswer",
    "RouterResult",
    "MockRouter",
    "get_router",
]
