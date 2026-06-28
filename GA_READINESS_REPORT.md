# GA Readiness Report

Date: 2026-06-28
Target Release: `v1.0.0`
Sprint: GA Readiness Sprint

## GA Blockers

| Blocker | Status | Evidence |
| --- | --- | --- |
| Render Plan must follow saved Timeline order | Fixed | Backend regression covers `Save Timeline -> Generate Render Plan -> Export Render Plan` with order `2,1,3`. |
| Coffee Demo must be self-contained | Fixed | `demo/coffee-commercial.json` now references checked-in demo image, keyframe, video, and audio fixtures. The workbench imports the demo through existing APIs. |

## What Changed

- Render plan generation now preserves repository shot order, which already reflects saved `timeline_order`.
- Coffee demo fixture now includes all referenced media files under `demo/assets` and `demo/audio`.
- Existing workbench page now has an `Import Demo` action that creates the demo project, imports storyboard text, registers demo assets, binds shot asset paths, and saves the fixture timeline.
- Frontend E2E smoke now covers Import Demo, Asset Library, Timeline reorder/save, Generate Render Plan, and Export Render Plan.
- README and demo guide now describe the first-run demo path.

## Out of Scope

- No new providers.
- No real Jimeng integration.
- No subtitles work.
- No dubbing work.
- No ffmpeg final rendering.
- No new API, page, or database table.

## Readiness Score

Readiness Score: 94/100

Remaining risk:

- The current frontend E2E smoke runs in Vitest/jsdom with mocked service calls. It covers the browser workflow component contract, while backend tests cover real persistence/export behavior.
- Provider-backed image/keyframe generation still depends on external settings and is not required for the self-contained demo.

## Validation

- Backend tests: `python -m pytest tests/video_workbench -v`
  - Result: passed, `141 passed`.
- Frontend install: `npm ci`
  - Result: passed.
- Frontend tests: `npm run test -- --run`
  - Result: passed, `54 passed`.
- Frontend build: `npm run build`
  - Result: passed.
- Frontend lint: `npm run lint`
  - Result: passed.
- E2E smoke: `npm run test:e2e`
  - Result: passed, `1 passed`.
- Ruff: `ruff check .`
  - Result: passed.
- Rendered browser demo validation:
  - Flow: Import Demo -> move Shot 2 up -> Save Timeline -> Generate Render Plan -> Export Render Plan.
  - Exported `render-plan.json` order: `2,1,3`.

## GA Recommendation

Recommendation: Yes, proceed toward `v1.0.0` GA.
