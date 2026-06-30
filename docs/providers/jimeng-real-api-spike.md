# Jimeng Real API Feasibility Spike

## Purpose

This spike is an opt-in check for early Jimeng real API feasibility. It is not a
production Jimeng integration and does not replace the mock provider.

The spike only verifies that:

- Jimeng credentials can be read from environment variables.
- The configured endpoint is syntactically valid and reachable.
- A submit task contract can be constructed.
- A poll result contract can be constructed.
- A download result contract can be constructed.

It does not connect the real Jimeng API to the `generate-video` workflow.

## Why It Is Skipped By Default

Real provider calls can require private credentials, network access, provider
quota, and paid account state. Default development and CI must remain runnable
without any real Jimeng account.

The test is skipped unless `RUN_JIMENG_SPIKE=1` is set.

## Required Environment Variables

```bash
export RUN_JIMENG_SPIKE=1
export JIMENG_ACCESS_KEY="<your-access-key>"
export JIMENG_SECRET_KEY="<your-secret-key>"
export JIMENG_ENDPOINT="https://example.provider.endpoint"
export JIMENG_MODEL="<jimeng-model-name>"
```

Use real values only in your local shell or secret manager. Do not commit them.

## How To Run

Default run, expected to skip:

```bash
python -m pytest backend/tests/provider_spikes -v
```

Opt-in local spike:

```bash
RUN_JIMENG_SPIKE=1 \
JIMENG_ACCESS_KEY="<your-access-key>" \
JIMENG_SECRET_KEY="<your-secret-key>" \
JIMENG_ENDPOINT="https://example.provider.endpoint" \
JIMENG_MODEL="<jimeng-model-name>" \
python -m pytest backend/tests/provider_spikes -v
```

## Expected Result

Without `RUN_JIMENG_SPIKE=1`, pytest should report the spike as skipped.

With all required variables set, the test should pass if the endpoint is
reachable and the local submit, poll, and download contracts can be constructed.
If the provider endpoint cannot be reached, the test fails with a message that
names the failing check without printing secrets.

## Failure Troubleshooting

- Missing environment variables: confirm all required variables are exported in
  the same shell that runs pytest.
- Invalid endpoint: `JIMENG_ENDPOINT` must be a complete `http` or `https` URL.
- Timeout or connection failure: confirm network access, VPN, proxy, firewall,
  and provider service availability.
- Unexpected HTTP status: confirm the endpoint base URL is correct for the
  account and region.
- Auth or quota errors in later manual experiments: confirm account status,
  permissions, quota, model name, and region with the provider.

## Safety Notes

- Do not print or log `JIMENG_SECRET_KEY`.
- Do not commit real credentials, tokens, signed URLs, or provider responses
  containing secrets.
- Do not paste real credentials into README examples, screenshots, fixtures, or
  issue comments.
- Rotate credentials immediately if they are exposed.

## Why This Does Not Enter CI

CI must stay deterministic, free of paid provider side effects, and runnable by
contributors without private Jimeng credentials. Provider contract tests remain
mocked and deterministic; this spike is for manual feasibility checks only.
