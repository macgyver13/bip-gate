# bip-gate

**BIP-correctness harness for agentic Bitcoin development.**

Coding agents draft; they never mark a lane green. `bip-gate` routes claims through a typed decision backend (mock by default, optional [Jev / TypeSafe](https://typesafe.systems)), then runs deterministic checkers and BIP test-vector oracles.

## Install

```bash
pip install -e ".[dev]"
# optional Jev backend:
pip install -e ".[jev]"
```

Requires Python ≥ 3.11.

## CLI

```bash
bip-gate lanes
bip-gate schema
bip-gate check --claim claims/example_sp_send.json
bip-gate check --psbt BASE64_OR_HEX
bip-gate check --file path.psbt --bip 375
```

Verdict JSON uses `pass | fail | need_human | not_implemented`.

## Router

| Env | Behavior |
|-----|----------|
| `BIP_GATE_ROUTER=mock` (default) | Heuristic Choice/Noul/Score answers — no API key |
| `BIP_GATE_ROUTER=jev` | Requires `typesafe-sdk` + `TYPESAFE_API_KEY` |

## Initial lanes

| id | BIP | MVP status |
|----|-----|------------|
| `psbt_174` | 174 | stub |
| `psbt_370` | 370 | stub |
| `sp_352` | 352 | stub |
| `sp_send_375` | 375 | **structural checker** |
| `sp_spend_376` | 376 | stub |
| `sp_desc_392` | 392 | stub |

See [ARCHITECTURE.md](ARCHITECTURE.md) and [CONTRIBUTING.md](CONTRIBUTING.md) (add a BIP lane in ~30 minutes).

## License

MIT © 2026 Mac G / macgyver13
