# Jimeng Security Checklist

## Purpose

This checklist defines the security requirements for a future production
Jimeng REST provider. It is documentation only. It does not add credentials,
signing, provider registration, HTTP calls, or CI real-provider execution.

## AK/SK Storage

- Store Volcano Engine `access_key` and `secret_key` outside the repository.
- Do not commit credentials in source files, tests, docs, fixtures, local
  snapshots, screenshots, or PR descriptions.
- Prefer deployment secret managers for production.
- Prefer local environment variables or an ignored local secret file for manual
  development.
- If provider settings later persist credentials, encrypt them at rest.
- Redact credentials in every API response, admin view, debug payload, and
  support export.

## Secret Rotation

- Use a dedicated Jimeng/Visual Service credential, not a personal admin key.
- Keep development, staging, and production credentials separate.
- Rotate credentials on a defined schedule.
- Rotate immediately after suspected exposure in logs, shell history, PRs, or
  screenshots.
- Support deploying a replacement key without database migration.
- Remove retired keys from local shells, CI variables, deployment secrets, and
  provider settings.
- Keep a short rotation runbook that names owner, validation steps, rollback
  steps, and revocation steps.

## Environment Variable Policy

Recommended environment variable names for a future provider:

- `JIMENG_ACCESS_KEY`
- `JIMENG_SECRET_KEY`
- `JIMENG_ENDPOINT`
- `JIMENG_REGION`
- `JIMENG_SERVICE`
- `JIMENG_VERSION`
- `JIMENG_REQ_KEY`

Policy:

- Documentation examples must use placeholders, never real values.
- CI must not require these variables for default tests.
- Local opt-in smoke tests must skip when required variables are missing.
- Deployment systems should mark AK/SK variables as secret.
- Application logs must not print environment variable values.
- Startup diagnostics may report whether a required variable is present, but
  must not report its value.

## Log Redaction

Redact or omit:

- `secret_key`
- `access_key` except for a short masked suffix when operationally necessary
- Authorization headers
- Signature headers and signature query parameters
- Canonical request strings
- Raw signed headers
- Full `video_url`
- Prompt text when logs can leave the trusted application boundary
- User-supplied media URLs when they may reveal private storage paths

Safe fields:

- Provider name
- Local job id
- Remote `task_id`
- Provider `request_id`
- Sanitized provider code
- Local error category
- Retry count
- Duration and timeout values

## Least Privilege

- Use a dedicated Volcano Engine sub-account or access key for the Jimeng REST
  provider.
- Grant only the minimum Visual Service permissions needed for submit and poll.
- Do not reuse owner, admin, billing, or personal credentials.
- Restrict production secret read access to the application runtime and a small
  operator group.
- Separate development and production accounts when practical.
- Disable or revoke unused keys.

## Credential Validation

- Validate required credential fields before sending any network request.
- Treat missing signing support as a hard configuration error.
- Use fake credentials in unit and contract tests.
- Keep real-account validation manual and opt-in.
- Do not add real AK/SK to GitHub Actions.
- Do not validate credentials by generating a video unless the operator has
  explicitly approved quota and cost use.
- Surface configuration failures without echoing credential values.

## Production Deployment Recommendations

- Keep the mock provider as the default until production Jimeng is explicitly
  enabled.
- Gate real Jimeng submission behind an operator-controlled configuration flag.
- Set conservative submit concurrency defaults.
- Configure per-project and per-run cost limits before enabling real submit.
- Export provider metrics without secret-bearing fields.
- Review logs and traces in staging before production rollout.
- Run one small manual smoke test before enabling broader use.
- Document rollback: disable the provider flag, keep existing local outputs,
  and stop submitting new Jimeng jobs.
