# Provider Runtime Guard Report

Date: 2026-06-30
Branch: `codex/provider-runtime-guards`
Scope: v1.1 PR 3, provider runtime guard hardening

## Runtime Guard Coverage

Added runtime guard coverage for the Jimeng provider job polling path:

- invalid provider response
- malformed JSON-like provider response
- empty provider response
- partial provider response
- missing local `submit_id`
- malformed local job payload
- missing download URL
- empty download
- truncated download
- invalid media download
- unexpected local job status
- unknown provider state
- invalid bind result
- duplicate bind attempt
- timeout retry exhaustion

Added deterministic failure fixtures in:

```text
backend/tests/provider_contract/fixtures.py
backend/tests/provider_contract/test_runtime_guards.py
```

Runtime implementation changes:

- Validate provider poll result shape and known states before download.
- Require completed provider results to include `result_url`.
- Validate downloaded video bytes before writing and binding.
- Convert provider response/download/bind failures into standard provider error
  responses.
- Preserve terminal-state polling guards.
- Avoid asset creation when bind fails.

## Remaining Runtime Risks

- Download validation is intentionally lightweight. It rejects empty, truncated,
  and clearly invalid fixture bytes, and accepts current deterministic mock
  outputs plus common MP4-like prefixes. A future real provider should add
  ffprobe or content-type validation before production use.
- There is still no explicit cancellation API or retry API. Cancellation and
  retry remain contract concepts, with runtime coverage limited to no implicit
  cancellation, terminal poll rejection, and timeout retry exhaustion.
- Real provider rate limits, auth failures, signed URL expiry, and large file
  limits remain unverified because real Jimeng integration is out of scope.
- Downloaded files can still be written before a later bind failure. The runtime
  now prevents asset creation and shot binding in that case, but orphan file
  cleanup remains a future hardening task.

## Validation

Provider contract and runtime guard suite:

```bash
python -m pytest backend/tests/provider_contract -v
```

Result:

```text
34 passed
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

## Real Jimeng Spike Recommendation

Do not start the real Jimeng Spike yet.

Recommended next step:

1. Run the full backend regression suite and merge the runtime guard PR after
   review.
2. Add a real Jimeng feasibility checklist with account, signing, quota, cost,
   and download URL expiry details.
3. Consider ffprobe-backed media validation before any real provider is marked
   supported.

After this PR is merged, it is reasonable to plan a narrow, opt-in real Jimeng
feasibility Spike. It should remain skipped by default and must not run in CI.
