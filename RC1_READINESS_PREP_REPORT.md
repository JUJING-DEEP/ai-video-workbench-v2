# RC1 Readiness Prep Report

## Summary

- Release baseline: `v1.0.0-beta.2`
- Target: prepare for `v1.0.0-rc.1`
- Estimated Readiness Score after this prep: **90 / 100**
- Recommendation: **Move to v1.0.0-rc.1 after PR review and CI confirmation**

This prep keeps the product scope unchanged. It does not add providers, AI models,
video generation capability, API capability, pages, or database tables.

## Added Files

- `demo/coffee-commercial.json`
- `frontend/e2e/video-workbench-smoke.spec.js`
- `backend/tests/video_workbench/test_demo_fixture.py`
- `RC1_READINESS_PREP_REPORT.md`

## E2E Coverage

The browser smoke test uses the existing frontend stack: Vitest, jsdom, Vue Test
Utils, and the current `VideoWorkbench.vue` UI.

Covered workflow:

1. Create Project
2. Import Storyboard into Shots
3. Upload Asset
4. Bind Asset to the selected Shot
5. Reorder Timeline
6. Save Timeline
7. Generate Render Plan
8. Export Render Plan

The test is intentionally mock-backed. It validates the browser/UI workflow and
frontend API orchestration without introducing Playwright, Cypress, a new backend
endpoint, or a new product feature.

## Demo Fixture

`demo/coffee-commercial.json` contains:

- Project: `Coffee Commercial Demo`
- Three shots covering image and key-node video workflows
- Asset entries for image, keyframe, and video paths
- Timeline ordering for three 4-second shots
- Render plan items for all three shots
- `storyboard_text` that can be pasted into the existing Storyboard Import UI

The fixture is importable through the existing manual workflow:

1. Create a project named `Coffee Commercial Demo`.
2. Paste `storyboard_text` into Storyboard Import.
3. Bind the listed asset paths.
4. Generate and export the render plan.

No dedicated demo import API was added.

## Jimeng Contract

Documentation and UI copy now describe the current Jimeng workflow as
**Jimeng REST Adapter (Mock)**.

Clarified contract:

- It is for workflow testing.
- It does not mean the real Volcano Engine Jimeng API is connected.
- Real integration is planned for a future release.

## Validation

- Backend tests: `139 passed`
- Frontend tests: `54 passed`
- Frontend build: passed
- Frontend lint: passed
- E2E smoke: `1 passed`
- Ruff: passed

## RC Recommendation

The original RC blockers are addressed:

- Version metadata is synchronized to `v1.0.0-beta.2`.
- Jimeng REST workflow is explicitly labeled as mock/scaffold.
- A minimal browser E2E smoke test covers the core demo workflow.
- A demo fixture exists and is validated by backend tests.
- README, SPEC, demo docs, and quickstart flow are synchronized.

Recommendation: **enter `v1.0.0-rc.1` after this PR passes GitHub Actions and
human review.**
