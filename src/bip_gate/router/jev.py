"""Optional Jev (TypeSafe System One) router backend.

Requires the ``[jev]`` extra (``typesafe-sdk``) and ``TYPESAFE_API_KEY``.
Falls back to a clear error if the SDK is missing.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any

from bip_gate.router.base import Router, RouterAnswer, RouterResult

try:
    import typesafe_sdk  # type: ignore[import-not-found]

    _HAS_TYPESAFE = True
except ImportError:  # pragma: no cover - exercised when extra not installed
    typesafe_sdk = None  # type: ignore[assignment]
    _HAS_TYPESAFE = False


def _digest(value: str | None) -> str | None:
    if not value:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


class JevRouter(Router):
    """Route via TypeSafe / Jev typed decisions when available."""

    backend_name = "jev"

    def route(self, claim: Any, lane_ids: list[str]) -> RouterResult:
        if not _HAS_TYPESAFE:
            raise RuntimeError(
                "Jev backend requested (BIP_GATE_ROUTER=jev) but typesafe-sdk "
                "is not installed. Install with: pip install 'bip-gate[jev]'"
            )
        api_key = os.environ.get("TYPESAFE_API_KEY")
        if not api_key:
            raise RuntimeError(
                "BIP_GATE_ROUTER=jev requires TYPESAFE_API_KEY in the environment"
            )

        artifacts = getattr(claim, "artifacts", None)
        state = {
            "summary": getattr(claim, "summary", "") or "",
            "asserted_bips": list(getattr(claim, "asserted_bips", None) or []),
            "artifact_digests": {
                "psbt_base64": _digest(
                    getattr(artifacts, "psbt_base64", None) if artifacts else None
                ),
                "psbt_hex": _digest(
                    getattr(artifacts, "psbt_hex", None) if artifacts else None
                ),
                "descriptor": _digest(
                    getattr(artifacts, "descriptor", None) if artifacts else None
                ),
            },
        }

        # Placeholder batch shape — real SDK wiring lands when typesafe-sdk API stabilizes.
        # We keep the same answer keys as the mock router for golden-test stability.
        _ = (typesafe_sdk, json.dumps(state), lane_ids)  # reserved for live call
        raise NotImplementedError(
            "Jev live client is scaffolded but not wired for MVP. "
            "Use BIP_GATE_ROUTER=mock, or contribute the typesafe-sdk call "
            "against the shared state/questions documented in ARCHITECTURE.md."
        )
