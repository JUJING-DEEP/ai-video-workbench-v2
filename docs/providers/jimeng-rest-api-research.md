# Jimeng REST API Research

Research date: 2026-06-30

## Scope

This document records official REST API findings for Jimeng / Dreamina video
generation and compares them with the current AI Video Workbench mock provider
contract and the Dreamina CLI surface.

No project runtime code was changed during this research.

## Sources Checked

- Volcano Engine Jimeng AI documentation:
  `https://www.volcengine.com/docs/85621/1777001`
- Official Jimeng AI PDF guide downloaded from the Volcano documentation route:
  `即梦AI_文档指南_1782790629.pdf`
- Volcano common response and error code reference:
  `https://www.volcengine.com/docs/6444/69728`
- Volcano Python SDK examples:
  `https://github.com/volcengine/volc-sdk-python`
- Volcano Go SDK examples:
  `https://github.com/volcengine/volc-sdk-golang`
- Dreamina CLI installer entry:
  `https://jimeng.jianying.com/cli`

## Official REST Shape

The public Jimeng video REST surface is part of Volcano Engine's Visual Service.
The current official video-generation documentation uses a generic async task
pattern:

- Endpoint: `https://visual.volcengineapi.com`
- HTTP method: `POST`
- Content-Type: `application/json`
- Submit action: `CVSync2AsyncSubmitTask`
- Poll action: `CVSync2AsyncGetResult`
- Version: `2022-08-31`
- Region: `cn-north-1`
- Service: `cv`
- Authentication: Volcano Engine AK/SK request signing through public
  parameters and signature headers.

The official SDK examples confirm the same shape through:

- Python: `VisualService().cv_sync2async_submit_task(form)`
- Python: `VisualService().cv_sync2async_get_result(form)`
- Go: `visual.DefaultInstance.CVSync2AsyncSubmitTask(reqBody)`
- Go: `visual.DefaultInstance.CVSync2AsyncGetResult(reqBody)`

## Authentication

The REST API is not a bearer-token API. It uses Volcano Engine access keys:

- `AccessKeyID` identifies the caller.
- `AccessKeySecret` signs requests and must be protected.
- The Jimeng video docs state fixed `Region=cn-north-1` and `Service=cv`.
- The SDK examples set AK/SK directly or read them from local Volcano SDK
  config.

Implementation implication: a real REST provider should not hand-roll signing
unless needed. Prefer the official Volcano SDK or a small, well-tested signing
adapter.

## Submit API

For Jimeng AI Video Generation 3.0 Pro, official submit uses:

```text
POST https://visual.volcengineapi.com?Action=CVSync2AsyncSubmitTask&Version=2022-08-31
```

Body fields for the documented 3.0 Pro flow:

```json
{
  "req_key": "jimeng_ti2v_v30_pro",
  "image_urls": ["https://example.com/keyframe.png"],
  "prompt": "generation prompt",
  "seed": -1,
  "frames": 121,
  "aspect_ratio": "16:9"
}
```

Important request rules:

- `req_key` is required.
- `prompt` is required for text-to-video.
- For image-to-video, image and prompt are both part of the documented example;
  `binary_data_base64` or `image_urls` can supply the single first-frame image.
- `binary_data_base64` and `image_urls` are alternatives.
- Image-to-video supports one first-frame image only for this 3.0 Pro API.
- Image input formats: JPEG and PNG.
- Base64 image max size: 4.7 MB.
- Max image resolution: `4096 x 4096`.
- Short side must be at least `320`.
- Long side to short side ratio must be within `3`.
- `frames` maps to duration: `121` for 5 seconds and `241` for 10 seconds.
- `aspect_ratio` values: `16:9`, `4:3`, `1:1`, `3:4`, `9:16`, `21:9`.
- For image-to-video, aspect ratio is selected from the input image and may
  involve centered cropping.

Submit success returns `code=10000` and `data.task_id`.

## Poll API

Official poll uses:

```text
POST https://visual.volcengineapi.com?Action=CVSync2AsyncGetResult&Version=2022-08-31
```

Body:

```json
{
  "req_key": "jimeng_ti2v_v30_pro",
  "task_id": "task id from submit",
  "req_json": "{\"aigc_meta\": {\"producer_id\": \"...\"}}"
}
```

`req_json` is optional and currently documented for implicit AIGC watermark /
metadata configuration.

Poll success returns `code=10000` and `data.status`.

Observed documented statuses:

- `in_queue`: task submitted
- `generating`: task consumed and processing
- `done`: completed; use outer `code` and `message` to distinguish success from
  failure
- `not_found`: no such task or expired after 12 hours
- `expired`: task expired; submit again

Some related Agent APIs also document `processing` as a pre-processing state.

## Download API

The official 3.0 Pro poll response returns:

```json
{
  "data": {
    "status": "done",
    "video_url": "https://..."
  }
}
```

The video URL is documented as valid for 1 hour. No separate download API was
found in the Jimeng 3.0 Pro REST docs. The provider should treat `video_url` as
a short-lived download URL and copy the media into local project storage before
binding it.

## Models And Service Keys

REST does not expose a CLI-style `model_version` for the 3.0 Pro API. It uses
`req_key` service identifiers.

Relevant public documentation found:

- `jimeng_ti2v_v30_pro`: Jimeng AI Video Generation 3.0 Pro text-to-video and
  first-frame image-to-video.
- `pippit_iv2v_cvtob`: Xiaoyunque / intelligent video Agent 1.0.
- `pippit_iv2v_v20_cvtob_with_vinput`: Xiaoyunque Agent 2.0 with references.

The PDF lists Jimeng AI Video Generation 3.0 720P and 1080P interface sections,
but their detailed sub-documents are not expanded in the extracted PDF. The
official navigation also marks several older 3.0 720P/1080P sub-documents as
offline or unavailable. Treat 3.0 Pro as the clearest currently documented REST
target for a first provider.

## Error Codes

Documented business errors include:

| HTTP | Code | Meaning | Retry |
| --- | --- | --- | --- |
| 200 | `10000` | success | no |
| 400 | `50411` | input image pre-check failed | no |
| 400 | `50511` | output image post-check failed | yes |
| 400 | `50412` | input text pre-check failed | no |
| 400 | `50512` | output text post-check failed | no |
| 400 | `50413` | text contains sensitive/copyright terms | no |
| 400 | `50516` | output video post-check failed | yes |
| 400 | `50517` | output audio post-check failed | yes |
| 400 | `50518` | input copyright image check failed | no |
| 400 | `50519` | output copyright image check failed | yes |
| 400 | `50520` | risk service internal error | no |
| 400 | `50521` | copyright text service error | no |
| 400 | `50522` | copyright image service error | no |
| 429 | `50429` | QPS limit reached | yes |
| 429 | `50430` | concurrency limit reached | yes |
| 500 | `50500` | internal error | yes for video docs |
| 500 | `50501` | internal RPC / algorithm error | yes for video docs |

Implementation implication: the local provider should distinguish retryable
provider errors from non-retryable validation and safety failures.

## Rate Limits, Quota, And Cost

Official public docs provide high-level limits and pricing, but not a stable
per-account QPS number.

Found:

- Video generation charges only when a video is successfully returned.
- Single API call returns one video.
- Billing is by generated video duration.
- Jimeng AI Video Generation 3.0 Pro: `1 RMB / second`.
- Jimeng AI Video Generation 3.0 1080P: `0.63 RMB / second`.
- Jimeng AI Video Generation 3.0 720P: `0.28 RMB / second`.
- S2.0 Pro: `0.65 RMB / second`.
- Default/free concurrency is documented as 1 for video generation.
- Paid concurrency is documented as 2 for several video generation products.
- QPS/resource packs can be purchased in the console.
- Usage, QPS/concurrency, error count, and latency are visible in the console.
- Resource packs can be purchased; after resource packs are exhausted, calls
  continue as pay-as-you-go if the account is active.
- Account arrears can lead to service suspension and resource release.

Missing from public docs:

- Exact default QPS for each account and service.
- Exact quota balance API for Jimeng REST.
- A public OpenAPI schema for the Visual Service Jimeng actions.
- A stable, machine-readable model catalog for Jimeng REST service keys.

## Current Mock Contract vs Official REST vs Dreamina CLI

| Area | Current Mock Contract | Official REST | Dreamina CLI |
| --- | --- | --- | --- |
| Auth | stored `access_key` and `secret_key` settings | Volcano AK/SK request signing | OAuth device login / local session |
| Endpoint | configurable endpoint, default-like placeholder | fixed `https://visual.volcengineapi.com` | hidden behind CLI |
| Model | free-form `model`, e.g. `jimeng-v3` | `req_key`, e.g. `jimeng_ti2v_v30_pro` | `model_version`, e.g. `seedance2.0fast` |
| Submit result | `submit_id` | `data.task_id` | `submit_id` in CLI output |
| Poll input | local job id + `submit_id` | `req_key` + `task_id` | `query_result --submit_id` |
| Processing status | `processing` | `in_queue`, `generating`, sometimes `processing` | `querying` / task status fields |
| Success status | `completed` after download and bind | `code=10000`, `data.status=done`, `video_url` | `gen_status=success` or queried result |
| Download | provider `result_url` then local copy | `video_url` valid for 1 hour | `query_result --download_dir` |
| Error model | timeout/provider/invalid response | structured `code`, `message`, `request_id` | CLI JSON / text output |
| CI fit | deterministic mock | not CI-safe by default | not CI-safe by default |

## Required Contract Adjustments For REST Provider

Likely changes for a real REST adapter:

- Rename internal provider setting from generic `model` to REST-facing
  `req_key`, or map `model` to `req_key` explicitly.
- Replace fake `submit_id` semantics with official `task_id` mapping.
- Add remote status mapping:
  - `in_queue` -> local `submitted` or `processing`
  - `generating` -> local `processing`
  - `done` + `code=10000` + `video_url` -> download then local `completed`
  - `not_found` / `expired` -> local `failed` with clear message
- Treat `video_url` as a short-lived download URL and persist a local copy.
- Validate image constraints before submit when practical.
- Include `request_id` in local error messages for debugging without exposing
  secrets.
- Add bounded retry/backoff for `50429`, `50430`, `50500`, and `50501`.
- Keep non-retryable moderation and copyright failures as local `failed`.
- Use SDK signing or a tested signing helper; do not place AK/SK in logs.

## Recommendation

Recommendation: continue REST Provider research and implementation planning.

Reasoning:

- REST aligns better with the current backend provider architecture.
- REST uses explicit AK/SK credentials and endpoint/service configuration.
- REST has a stable submit/poll/download lifecycle that maps to existing
  contract tests.
- REST can be mocked deterministically for CI.
- Dreamina CLI is useful for local comparison but depends on OAuth login state
  and opaque binary behavior.

The next step should be a narrow REST adapter design document, not production
integration code.

## PR 5 Adapter Skeleton Notes

The first adapter skeleton should stay offline-only:

- Build the official submit and poll request shapes.
- Parse fake HTTP response payloads that match official examples.
- Validate the one-hour `video_url` download contract.
- Map provider task statuses into local job statuses.
- Preserve a signing interface placeholder without signing or sending real
  requests.

The skeleton must not:

- call `https://visual.volcengineapi.com`
- require real AK/SK
- run in CI against the real provider
- replace the mock provider
- use Dreamina CLI as a provider path

Real Volcano signing should be implemented in a later PR, preferably through
the official SDK or a focused signing helper with separate tests.
