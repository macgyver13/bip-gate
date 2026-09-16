# Architecture

## Flow

```
Claim JSON / PSBT artifact
        │
        ▼
   Router (mock | jev)
   Choice / Noul / Score
        │
        ▼
 Lane selection + dependency closure
        │
        ▼
 Deterministic lane checkers (+ BIP vectors)
        │
        ▼
 Verdict JSON (pass|fail|need_human|not_implemented)
```

LLMs may draft claims and code; **only checkers** emit lane status. The router never writes `pass`.

## Packages

| Path | Role |
|------|------|
| `schema.py` | Pydantic `Claim` / `Verdict` |
| `router/` | `MockRouter` (default), optional `JevRouter` |
| `lanes/` | Plugin registry + per-BIP checkers |
| `oracles/vectors/` | Pointers to public BIP fixtures |

## Router question batch

Shared `state` = claim summary + artifact digests + asserted BIPs.

| id | type | purpose |
|----|------|---------|
| `primary_lane` | Choice | registered lane ids + `other` |
| `is_silent_payments_related` | Noul | soft SP bias |
| `touches_psbt` | Noul | soft PSBT bias |
| `merge_risk` | Score | low/medium/high/critical |

Code maps answers → lane set (union with `asserted_bips` and dependency closure), then runs allowlisted checkers only.

## BIP375 structural checker (`sp_send_375`)

Stdlib-only PSBT map walk:

- Detect PSBT (base64 or hex) via magic `psbt\xff`
- Parse global / input / output maps
- Per output: `PSBT_OUT_SCRIPT` (0x04, BIP370) vs `PSBT_OUT_SP_V0_INFO` (0x09, BIP375)
- Incomplete SP send (info without script) → `fail` if `claimed_complete`, else `need_human`
- Parse errors → `fail` (closed)
- Crypto / DLEQ verify → not wired → would be `need_human`

## Design principles

1. General BIP harness (registry of lanes), not SP-only
2. Jev decides; code enforces thresholds and tool allowlists
3. Mock-first for community use without TypeSafe early access
4. Machine verdict for CI / agent loops
5. No secrets in fixtures
