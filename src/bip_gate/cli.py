"""bip-gate CLI: lanes, check, schema."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from bip_gate.lanes.registry import list_lanes, resolve_lanes
from bip_gate.router import get_router
from bip_gate.schema import (
    Claim,
    ClaimArtifacts,
    CheckResult,
    RouterAnswer,
    RouterPayload,
    Verdict,
)


def _claim_from_args(args: argparse.Namespace) -> Claim:
    if getattr(args, "claim", None):
        path = Path(args.claim)
        data = json.loads(path.read_text(encoding="utf-8"))
        return Claim.model_validate(data)

    artifacts = ClaimArtifacts()
    if getattr(args, "psbt", None):
        raw = args.psbt.strip()
        # Heuristic: hex vs base64
        if all(c in "0123456789abcdefABCDEF" for c in raw) and len(raw) % 2 == 0:
            artifacts.psbt_hex = raw
        else:
            artifacts.psbt_base64 = raw
    if getattr(args, "file", None):
        blob = Path(args.file).read_bytes()
        # Prefer base64 representation for JSON-friendly claims
        import base64

        artifacts.psbt_base64 = base64.b64encode(blob).decode("ascii")

    asserted: list[int] = []
    if getattr(args, "bip", None):
        asserted = [int(x) for x in args.bip]

    return Claim(
        summary=getattr(args, "summary", None) or "CLI PSBT check",
        artifacts=artifacts,
        asserted_bips=asserted or [375],
        claimed_complete=bool(getattr(args, "claimed_complete", False)),
    )


def _router_payload(result: Any) -> RouterPayload:
    answers = {
        k: RouterAnswer(
            type=v.type,
            choice=v.choice,
            probability=v.probability,
            score=v.score,
            confidence=v.confidence,
        )
        for k, v in result.answers.items()
    }
    return RouterPayload(backend=result.backend, answers=answers)


def cmd_lanes(_args: argparse.Namespace) -> int:
    rows = []
    for lane in list_lanes():
        m = lane.meta
        rows.append(
            {
                "id": m.id,
                "bip": m.bip,
                "title": m.title,
                "dependencies": m.dependencies,
                "status": m.status,
            }
        )
    print(json.dumps(rows, indent=2))
    return 0


def cmd_schema(_args: argparse.Namespace) -> int:
    schema = {
        "claim": Claim.model_json_schema(),
        "verdict": Verdict.model_json_schema(),
    }
    print(json.dumps(schema, indent=2))
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    claim = _claim_from_args(args)
    router = get_router()
    lane_ids = [lane.meta.id for lane in list_lanes()]
    try:
        routed = router.route(claim, lane_ids)
    except (RuntimeError, NotImplementedError) as exc:
        verdict = Verdict(
            verdict="need_human",
            lanes_fired=[],
            router=RouterPayload(backend=getattr(router, "backend_name", "unknown")),
            checks=[],
            blockers=[str(exc)],
        )
        print(verdict.model_dump_json(indent=2))
        return 2

    lanes = resolve_lanes(routed, claim)
    blockers: list[str] = []
    if not lanes:
        blockers.append(
            "No lanes selected; see CONTRIBUTING.md to add a BIP lane, "
            "or set asserted_bips / provide PSBT artifacts"
        )
        # Emit a catch-all need_human check
        checks = [
            CheckResult(
                lane="generic",
                status="need_human",
                evidence=(
                    "Catch-all: could not map claim to a registered lane. "
                    "Documented path: add a lane in ~30 minutes (CONTRIBUTING.md)."
                ),
                refs=["CONTRIBUTING.md"],
            )
        ]
        verdict = Verdict.from_checks(
            lanes_fired=["generic"],
            router=_router_payload(routed),
            checks=checks,
            blockers=blockers,
        )
    else:
        checks = [lane.check(claim) for lane in lanes]
        verdict = Verdict.from_checks(
            lanes_fired=[lane.meta.id for lane in lanes],
            router=_router_payload(routed),
            checks=checks,
            blockers=blockers,
        )

    print(verdict.model_dump_json(indent=2))
    if verdict.verdict == "pass":
        return 0
    if verdict.verdict == "fail":
        return 1
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bip-gate",
        description="BIP-correctness harness for agentic Bitcoin development",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_lanes = sub.add_parser("lanes", help="List registered BIP lanes")
    p_lanes.set_defaults(func=cmd_lanes)

    p_schema = sub.add_parser("schema", help="Print Claim/Verdict JSON schemas")
    p_schema.set_defaults(func=cmd_schema)

    p_check = sub.add_parser("check", help="Route + check a claim or PSBT")
    p_check.add_argument("--claim", help="Path to claim JSON file")
    p_check.add_argument("--psbt", help="PSBT as hex or base64")
    p_check.add_argument("--file", help="Path to raw .psbt bytes")
    p_check.add_argument(
        "--bip",
        action="append",
        help="Asserted BIP number (repeatable); default 375 for --psbt/--file",
    )
    p_check.add_argument("--summary", help="Claim summary override")
    p_check.add_argument(
        "--claimed-complete",
        action="store_true",
        help="Mark claim as asserting a finalized/complete send",
    )
    p_check.set_defaults(func=cmd_check)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    code = args.func(args)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
