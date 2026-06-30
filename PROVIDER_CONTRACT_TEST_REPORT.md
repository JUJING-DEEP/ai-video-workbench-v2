# Provider Contract Test Report

Date: 2026-06-30
Branch: `codex/provider-contract-tests`
Scope: v1.1 PR 2, provider contract coverage

## Contract Coverage

Added a deterministic provider contract suite under:

```text
backend/tests/provider_contract/
```

Coverage includes:

- submit job contract
- poll job contract
- download result contract
- bind asset contract
- timeout behavior
- cancellation semantics at the contract-adapter level
- retry semantics at the contract-adapter level
- provider error behavior
- invalid credential rejection
- invalid response handling at the contract-adapter level
- malformed payload rejection
- terminal-state polling rejection
- no binding for failed, timed-out, or rejected jobs

The suite has two layers:

- Generic contract compliance tests using deterministic mock and future-real
  provider adapters.
- Current Jimeng REST workflow tests through the existing FastAPI routes and
  mock Jimeng provider dependency.

## Missing Cases

The current runtime still has contract gaps that should be addressed before any
real Jimeng implementation:

- Unknown provider poll statuses are not rejected by the runtime. The current
  route treats an unrecognized non-processing/non-failed status as completed.
- Download failures are not converted into the standard provider error envelope.
  A provider download exception currently surfaces as a server error and leaves
  the job in its previous submitted state.
- Cancellation is covered only at the generic contract-adapter level because the
  product has no cancellation API or lifecycle state yet.
- Retry is covered only as explicit bounded contract behavior and as a runtime
  guard against implicit retry by re-polling terminal jobs. The product has no
  retry API yet.

These gaps are intentionally reported rather than fixed in PR 2 because this PR
must not modify provider lifecycle, business API, or runtime behavior.

## Validation

Provider contract suite:

```bash
python -m pytest backend/tests/provider_contract -v
```

Result:

```text
21 passed
```

Backend regression suite:

```bash
cd backend
python -m pytest tests/video_workbench -v
```

Result:

```text
141 passed
```

## Real Jimeng Recommendation

Do not start real Jimeng implementation yet.

Recommended next step:

1. Close the missing runtime guards for invalid provider statuses and download
   failures.
2. Keep cancellation and retry out of scope unless the product explicitly adds a
   lifecycle/API for them.
3. Add an opt-in, skipped-by-default real Jimeng feasibility smoke only after the
   runtime guards are closed and credential/cost controls are documented.

The project should continue v1.1 with provider contract hardening before any
real provider connection.
