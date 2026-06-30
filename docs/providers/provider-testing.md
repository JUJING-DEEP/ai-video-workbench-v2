# Provider Contract Testing

This guide explains how to validate whether a video provider conforms to the
AI Video Workbench provider contract.

## Scope

Provider contract tests verify the lifecycle expected by the existing Jimeng
job workflow:

```text
submit -> poll -> download -> bind
```

The tests are deterministic and do not call external networks. They are designed
for the current mock Jimeng workflow and for any future real Jimeng provider
adapter.

## Test Location

```text
backend/tests/provider_contract/
```

Key files:

- `fixtures.py`: deterministic provider fixtures, API harness, and contract
  adapter helpers.
- `test_contract_interface.py`: generic provider contract compliance tests.
- `test_jimeng_api_contract.py`: current Jimeng REST workflow contract tests
  through the existing FastAPI routes.
- `test_runtime_guards.py`: runtime validation tests for malformed provider
  states, failed downloads, invalid bind results, and retry exhaustion.

## Running Provider Contract Tests

From the repository root:

```bash
python -m pytest backend/tests/provider_contract -v
```

These tests must pass without real provider credentials.

## What A Provider Must Prove

A conforming provider must prove:

- `submit` accepts a valid keyframe payload and returns a non-empty submit id.
- `poll` preserves `processing` jobs and maps terminal provider states safely.
- `download` happens only after provider completion.
- `bind` happens only after a video result has been downloaded.
- Failed, timed-out, malformed, or rejected jobs do not bind video output paths.
- Terminal jobs are not polled again as an implicit retry.
- Cancellation is explicit and must not happen as a side effect of polling.
- Retry is explicit, bounded, and limited to failed or timed-out jobs.
- Invalid credentials are rejected before provider submission.
- Malformed payloads are rejected before provider submission.
- Invalid provider responses are not silently treated as successful completion.

## Runtime Guard Checklist

Provider runtime guards must cover:

- invalid provider response objects
- malformed JSON-like provider payloads
- empty provider responses
- partial provider responses missing required fields
- missing local `submit_id`
- unexpected local job statuses
- unknown provider states
- missing download URLs
- empty downloads
- truncated downloads
- invalid media downloads
- provider download errors
- provider download timeouts
- invalid bind results
- duplicate bind attempts
- timeout retry exhaustion

Expected runtime behavior:

- Mark provider response, download, and bind failures as local `failed` jobs.
- Mark provider timeout failures as local `timeout` jobs.
- Preserve the standard error envelope.
- Do not create video assets for failed or timed-out jobs.
- Do not bind shot `video_path` for failed or timed-out jobs.
- Reject terminal-job polling instead of treating it as retry.

## Adding A Future Real Jimeng Adapter

Before connecting a real Jimeng provider, add a test adapter that satisfies the
same contract interface used by `test_contract_interface.py`.

The adapter must remain skipped or mocked by default unless explicit integration
credentials and opt-in flags are present. Real provider calls must never run in
default CI.

## Runtime Guard Tracking

If a new provider behavior cannot be enforced yet, record the gap in the current
provider report and do not claim real-provider readiness until the gap is
closed.
