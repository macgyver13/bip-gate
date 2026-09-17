# Example claims

Practical scenarios for evaluating `bip-gate` (mock or Jev).

| File | Scenario | Likely lanes | Notes |
|------|----------|--------------|-------|
| `example_sp_send.json` | Original incomplete SP send | 375→370,352 | `need_human` on 375 |
| `01_sp_send_incomplete.json` | Draft SP send | 375 | info, no script |
| `02_sp_send_complete_structural.json` | Finalized SP send | 375 | structural `pass` on 375; stubs elsewhere |
| `03_sp_send_claimed_complete_but_missing_script.json` | Agent over-claims | 375 | should `fail` |
| `04_psbt_output_missing_script_and_sp.json` | Invalid output map | 375 | `fail` |
| `05_not_a_psbt.json` | Garbage blob | 375 | `fail` |
| `06_psbt_v2_plain_p2tr.json` | Non-SP PSBTv2 | 370 | 375 soft-bias may still fire via deps if asserted only 370 |
| `07_sp_spend_utxo.json` | SP spend | 376,352 | stub → `not_implemented` |
| `08_sp_descriptor_watch_only.json` | Descriptor import | 392,352 | stub |
| `09_ambiguous_agent_comment.json` | No BIPs / no artifacts | generic | catch-all `need_human` |
| `10_mixed_sp_and_plain_outputs.json` | Mixed outputs | 375 | incomplete SP → `need_human` |
| `11_sp_info_bad_length.json` | Truncated SP info | 375 | `fail` |
| `12_sp_label_without_info.json` | Label w/o info | 375 | `fail` |
| `13_sp_send_claim_no_artifact.json` | Text-only claim | 375 | `need_human` |
| `14_psbt_v0_legacy_roles.json` | BIP174 focus | 174 | stub |

```bash
# mock (default)
for f in claims/*.json; do echo "=== $f"; bip-gate check --claim "$f" | jq -c '{file:"'$f'", verdict, lanes: .lanes_fired, primary: .router.answers.primary_lane.choice}'; done

# Jev
export BIP_GATE_ROUTER=jev TYPESAFE_API_KEY=…
bip-gate check --claim claims/02_sp_send_complete_structural.json
```

## Unsupported / non-PSBT scenarios (MuSig2, key agg, DLEQ)

These assert BIP numbers **not** in the lane registry (`327`, `374`, `390`, `328`, …).
Expected behavior today:

- Mock/Jev `primary_lane` often `other` (or an SP/PSBT lane only if those BIPs are also asserted)
- Unregistered BIP numbers do **not** invent a checker
- If no registered lane is selected → `generic` / `need_human` and CONTRIBUTING pointer
- If a registered BIP is also asserted (e.g. 352) → that stub lane may still fire; MuSig2 itself stays ungated

| File | Scenario | Asserted BIPs |
|------|----------|---------------|
| `15_musig2_key_agg_bip327.json` | BIP327 key aggregation only | 327 |
| `16_musig2_signing_session_bip327.json` | BIP327 signing session | 327 |
| `17_musig_descriptor_bip390.json` | BIP390 `musig()` descriptor | 390 |
| `18_dleq_proof_bip374.json` | BIP374 DLEQ (no PSBT) | 374 |
| `19_key_agg_agent_overclaim.json` | Overconfident ship-it | 327, 340 |
| `20_musig2_into_silent_payments.json` | MuSig2 spend key + SP descriptor | 327, 352, 392 |
| `21_ask_gate_unknown_bip.json` | Explicit unknown-BIP ask | 328 |

Adding a real lane later: follow [CONTRIBUTING.md](../CONTRIBUTING.md) (`musig_327`, `dleq_374`, `musig_desc_390`, …).
