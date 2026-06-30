# Jimeng REST Adapter Skeleton

## Purpose

The Jimeng REST adapter skeleton captures the official Volcano Engine request
and response contract without making real provider calls.

It is a foundation for future integration work only. It does not replace the
mock provider, does not run real Jimeng calls in CI, and does not require real
AK/SK credentials.

## Official REST Defaults

Current defaults are based on Research Sprint 1:

| Field | Value |
| --- | --- |
| endpoint | `https://visual.volcengineapi.com` |
| submit action | `CVSync2AsyncSubmitTask` |
| poll action | `CVSync2AsyncGetResult` |
| version | `2022-08-31` |
| region | `cn-north-1` |
| service | `cv` |
| req_key | `jimeng_ti2v_v30_pro` |

## What The Skeleton Does

The skeleton supports:

- `build_submit_request(...)`
- `parse_submit_response(...)`
- `build_poll_request(...)`
- `parse_poll_response(...)`
- `validate_video_url(...)`
- `map_provider_status(...)`

It builds request objects containing:

- method
- endpoint
- query parameters
- headers
- JSON body
- region
- service
- a `signing_required` marker

The request object is intentionally inert. It is not sent over the network by
this PR.

## Submit Contract

Submit request shape:

```text
POST https://visual.volcengineapi.com?Action=CVSync2AsyncSubmitTask&Version=2022-08-31
```

Body:

```json
{
  "req_key": "jimeng_ti2v_v30_pro",
  "image_urls": ["https://assets.example/keyframe.png"],
  "prompt": "camera slowly pushes in",
  "seed": -1,
  "frames": 121,
  "aspect_ratio": "16:9"
}
```

Submit success requires:

```json
{
  "code": 10000,
  "data": {
    "task_id": "7392616336519610409"
  }
}
```

The adapter maps `task_id` to the local provider submission id concept.

## Poll Contract

Poll request shape:

```text
POST https://visual.volcengineapi.com?Action=CVSync2AsyncGetResult&Version=2022-08-31
```

Body:

```json
{
  "req_key": "jimeng_ti2v_v30_pro",
  "task_id": "7392616336519610409"
}
```

Supported provider status mapping:

| Provider status | Local status |
| --- | --- |
| `in_queue` | `processing` |
| `generating` | `processing` |
| `processing` | `processing` |
| `done` | `completed` |
| `not_found` | provider error |
| `expired` | provider error |

Completed poll responses must contain `video_url`.

## Download URL Contract

The official poll response returns a `video_url` when generation is complete.
The URL is documented as valid for 1 hour.

The skeleton only validates that `video_url` is an HTTP(S) URL. A later provider
implementation must download the video within the validity window and persist a
local project copy before binding the shot output path.

## Signing Boundary

Real Volcano signing is out of scope for this PR.

The skeleton records the request's `region`, `service`, and
`signing_required=True` so the future signing layer has an explicit interface.
It does not:

- construct Authorization headers
- calculate signatures
- send AK/SK over the network
- log credential values

Future signing work should prefer the official Volcano SDK or a narrow signing
helper with isolated tests.

## CLI Boundary

Dreamina CLI is not a provider for v1.1.

The CLI remains useful for local manual comparison and debugging, but it uses
OAuth session state and command output rather than the official Visual Service
AK/SK REST contract. It must not be wired into backend provider selection or
CI.

## CI Policy

CI should run only deterministic tests with fake payloads. Real Jimeng REST
calls, real AK/SK, and quota-consuming provider requests must remain opt-in and
outside the default test suite.
