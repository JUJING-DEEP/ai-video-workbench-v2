# Jimeng Provider Contract

Baseline: `v1.0.0`
Target release: `v1.1`

## Current Status

The current Jimeng integration wires the business video-job API to the signed
Jimeng REST submit and poll clients. It validates the local provider lifecycle
for video jobs, including provider settings, job submission, polling, remote
`video_url` retrieval, remote asset creation, shot binding, and render-plan
readiness.

It does not download generated video files to local storage in this slice. A
later FFmpeg/rendering slice owns local media download and normalization.

## v1.1 Submit Integration Boundary

The first production integration slice adds a signed Jimeng REST submit client
behind an injectable HTTP transport. This client can:

- Build the official `CVSync2AsyncSubmitTask` request.
- Sign the submit request with the reusable Volcengine V4 signer.
- Send the signed request through a caller-provided transport.
- Parse the official `data.task_id` submit response.
- Map submit provider errors and transport timeouts to local provider errors.

The business provider now uses the signed REST client path by default. Tests
inject deterministic clients or transports so contract and CI coverage remain
mocked by default.

## v1.1 Poll And Retrieve Boundary

The second production integration slice adds a signed Jimeng REST poll client
behind an injectable HTTP transport. This client can:

- Build the official `CVSync2AsyncGetResult` request.
- Sign the poll request with the reusable Volcengine V4 signer.
- Send the signed request through a caller-provided transport.
- Map remote processing states to local `processing`.
- Map completed responses to a validated `video_url`.
- Reject failed, expired, missing, malformed, timed out, or unsigned poll
  states with stable provider errors.

This slice retrieves the remote `video_url` and binds that URL to the shot video
path through the existing business API. It does not download the video, write
local media files, add a poll loop, or change the public business API.

## Mock Provider And Real Provider Boundary

The mock provider is responsible for deterministic local behavior:

- Validate local settings and shot prerequisites.
- Create a local video generation job.
- Return stable job states for tests.
- Simulate provider errors and timeouts.
- Simulate completed remote `video_url` results.
- Bind completed remote URLs to the asset library and shot video path.

Real provider work uses the existing `jimeng` provider identity and lifecycle.
It must not add a new provider, new API, new database table, or new frontend
page.

## Lifecycle Contract

### Submit

Submit creates a local video generation job and sends the keyframe plus I2V
request to the provider implementation.

Required local prerequisites:

- Project exists.
- Shot exists.
- Shot has a non-empty `keyframe_path`.
- Jimeng provider settings are enabled.
- Required Jimeng credentials and non-secret config fields are present.

Expected local result:

- A job is created with `provider: "jimeng"`.
- A successful provider submission stores a non-empty `submit_id`.
- The job status becomes `submitted`.
- Submission failure changes the job to `failed` or `timeout`.

### Poll

Poll checks the remote or mock provider state for a submitted job.

Allowed local states before polling:

- `submitted`
- `processing`

Rejected local states:

- `completed`
- `failed`
- `timeout`
- any job without a `submit_id`

Expected local result:

- Provider `processing` maps to local `processing`.
- Provider `failed` maps to local `failed`.
- Provider `completed` proceeds to remote `video_url` binding before local
  completion.
- Provider timeout maps to local `timeout`.
- Provider error maps to local `failed`.

### Retrieve

Retrieve validates the completed remote `video_url` after the provider reports a
successful terminal state.

Expected local behavior:

- A valid HTTP(S) `video_url` is required before the local job becomes
  `completed`.
- The remote `video_url` is recorded as a video asset with `source: "jimeng"`.
- Invalid or missing result URLs must not create completed jobs or bind partial
  outputs.
- Local file download is out of scope for this slice.

### Bind

Bind happens only after `video_url` validation and remote asset creation
succeed.

Expected local behavior:

- Create a `video` asset with `source: "jimeng"`.
- Bind the remote `video_url` asset path to the shot video path.
- Update the job with `status: "completed"`, `result_url`, and `output_path`.
- Keep render-plan generation based on the bound shot video path.

## Request Contract

The local Jimeng job request is represented by the existing project and shot
state plus provider settings.

Submit input:

```json
{
  "project_id": 1,
  "shot_id": 1,
  "provider": "jimeng",
  "keyframe_path": "data/uploads/1/generated/keyframes/shot-001.png",
  "settings": {
    "enabled": true,
    "access_key": "<secret>",
    "secret_key": "<secret>",
    "region": "cn-north-1",
    "endpoint": "https://open.volcengineapi.com",
    "model": "jimeng-v3"
  }
}
```

Poll input:

```json
{
  "job_id": 501,
  "submit_id": "provider-submit-id",
  "provider": "jimeng"
}
```

Credential values are internal-only. They must never appear in public API
responses, frontend prefill state, logs, test snapshots, or documentation
fixtures.

## Response Contract

Public API responses use the standard response envelope.

Submitted job response:

```json
{
  "success": true,
  "data": {
    "job": {
      "id": 501,
      "project_id": 1,
      "shot_id": 1,
      "provider": "jimeng",
      "status": "submitted",
      "submit_id": "provider-submit-id",
      "result_url": "",
      "output_path": "",
      "error_message": ""
    }
  }
}
```

Completed job response:

```json
{
  "success": true,
  "data": {
    "job": {
      "id": 501,
      "project_id": 1,
      "shot_id": 1,
      "provider": "jimeng",
      "status": "completed",
      "submit_id": "provider-submit-id",
      "result_url": "https://provider.example/result.mp4",
      "output_path": "https://provider.example/result.mp4",
      "error_message": ""
    }
  }
}
```

Error response:

```json
{
  "success": false,
  "error": {
    "code": "provider_timeout",
    "message": "Jimeng provider request timeout."
  }
}
```

## Job Status Contract

| Status | Meaning | Can poll? | Can bind output? |
| --- | --- | --- | --- |
| `pending` | Local job exists but is not submitted. | No | No |
| `submitted` | Provider accepted the job and returned a submit id. | Yes | No |
| `processing` | Provider reports that generation is still running. | Yes | No |
| `completed` | Remote `video_url` retrieval, asset creation, and shot binding succeeded. | No | Yes |
| `failed` | Provider or local lifecycle failed. | No | No |
| `timeout` | Submit, poll, or total job timeout occurred. | No | No |

Unknown remote states must not be treated as completed. They should either map
to `processing` within a bounded timeout or fail with a clear local error.

## Error Handling Contract

Provider errors must produce stable local behavior:

- Missing project or shot: return `404`.
- Missing keyframe: return `400`.
- Disabled provider: return `403`.
- Missing Jimeng credentials or required settings: return `400`.
- Polling a terminal job: return `409`.
- Polling a job without `submit_id`: return `409`.
- Provider validation, quota, auth, or remote failure: mark job `failed`.
- Provider timeout: mark job `timeout`.
- Missing or invalid completed `video_url`: mark job `failed`.

Failed, timed-out, or rejected jobs must not bind a video path to the shot.

## Timeout Contract

The provider lifecycle has separate timeout categories:

- Submit timeout: provider did not accept the job in time.
- Poll timeout: one provider status request timed out.
- Total job timeout: job stayed non-terminal longer than the configured limit.

Timeout behavior:

- Persist `status: "timeout"` with a clear `error_message`.
- Do not mark the job completed.
- Do not bind partial outputs.
- Keep real-provider timeout settings explicit and documented.

## Credential Safety Rules

- Public GET and PUT provider settings responses must return credential presence
  booleans only.
- Frontend forms must not prefill saved credential values.
- Logs must not include API keys, access keys, secret keys, signatures, or signed
  URLs containing secret-bearing query parameters.
- Test fixtures must use fake credentials or redacted placeholders.
- Local SQLite plaintext storage remains a trusted-local limitation unless a
  later release explicitly adopts OS or environment secret storage.

## Cost, Quota, And Rate Limit Considerations

Real provider calls may consume paid quota. Contract and CI tests must remain
mocked by default.

Real-provider tests must be:

- skipped unless explicit credentials and an explicit opt-in flag are present
- limited to one short controlled job unless manually overridden
- excluded from default CI
- documented with expected cost and quota risk
- safe against repeated paid submissions caused by retry loops

Automatic retries must not resubmit paid generation jobs by default. Safe retry
behavior may be considered only for idempotent polling.

## Real Integration Prerequisites

Before connecting the real Jimeng API, the project must confirm:

- Account access is approved for the target Jimeng video model.
- Official endpoint, region, model name, and request schema are verified.
- Authentication and signing are implemented from official documentation.
- Submit, poll, completed, failed, and timeout responses are observed.
- One short controlled job can be submitted, polled, retrieved as a remote
  `video_url`, bound, and exported into a render plan.
- Credential values do not appear in API responses, frontend state, logs, or
  test output.
- Cost, quota, rate limits, and failure modes are documented.
- Real integration tests are opt-in and skipped in default CI.

If any prerequisite is not met, `v1.1` should ship contract hardening only and
defer real Jimeng integration.
