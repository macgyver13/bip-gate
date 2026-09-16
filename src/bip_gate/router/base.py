"""Abstract router interface shared by mock and Jev backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal


AnswerType = Literal["choice", "noul", "score"]


@dataclass
class RouterAnswer:
    type: AnswerType
    choice: str | None = None
    probability: float | None = None
    score: str | None = None
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "choice": self.choice,
            "probability": self.probability,
            "score": self.score,
            "confidence": self.confidence,
        }


@dataclass
class RouterResult:
    backend: str
    answers: dict[str, RouterAnswer] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "backend": self.backend,
            "answers": {k: v.to_dict() for k, v in self.answers.items()},
        }


class Router(ABC):
    """Route a claim to typed answers used for lane selection."""

    backend_name: str = "base"

    @abstractmethod
    def route(self, claim: Any, lane_ids: list[str]) -> RouterResult:
        """Answer the shared Jev-shaped question batch for ``claim``."""
