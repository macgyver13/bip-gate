# Contributing

## Add a BIP lane in ~30 minutes

1. **Pick an id** — snake_case, usually `{area}_{bip}` (e.g. `taproot_341`).

2. **Create** `src/bip_gate/lanes/<id>.py`:

```python
from typing import Any
from bip_gate.lanes.base import Lane, LaneMeta
from bip_gate.schema import CheckResult

class MyLane(Lane):
    meta = LaneMeta(
        id="taproot_341",
        bip=341,
        title="Taproot",
        dependencies=["psbt_174"],  # or []
        status="stub",  # then partial / implemented
    )

    def check(self, claim: Any) -> CheckResult:
        # Start with stub_result; replace with structural rules + vector refs
        return self.stub_result()
```

3. **Register** in `src/bip_gate/lanes/registry.py`:
   - Import the module
   - Append an instance in `_build_registry()`
   - Add `BIP_TO_LANE[341] = "taproot_341"`

4. **Mock router** (optional): extend `_BIP_TO_LANE` / keywords in `router/mock.py` so heuristics can select the lane.

5. **Fixtures** — add public-only vectors under `tests/fixtures/` and point to upstream BIP vectors in `oracles/vectors/README.md`. **No private keys.**

6. **Tests** — `tests/test_<id>.py` covering pass/fail/need_human/not_implemented as applicable.

7. **Run**

```bash
pip install -e ".[dev]"
pytest
bip-gate lanes   # your id should appear
```

### Checker rules of thumb

- Fail closed on parse errors
- Use `need_human` when crypto or policy judgment is required but not wired
- Use `not_implemented` only for intentional stubs
- Cite BIP section URLs in `refs`

### PR checklist

- [ ] Lane registered and listed by `bip-gate lanes`
- [ ] Tests green in CI
- [ ] No secrets / API keys
- [ ] Docs mention the new BIP if user-facing
