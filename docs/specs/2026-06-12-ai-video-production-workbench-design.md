# AI Short Video Production Workbench Design

## Summary

Build a local web workbench for scaling an AI short-video workflow from storyboard text to aligned final video. The system will parse Google AI Studio storyboard batches, manage image/video generation tasks, track assets, validate dependencies and timing, generate subtitles, and export final videos with audio, visuals, and subtitles aligned.

The long-term system includes browser agents for Google AI Studio, Nano banana, and Jimeng. The first implementation focuses on a stable local MVP: storyboard parsing, shot management, prompt package export, asset import, validation, subtitles, and FFmpeg rendering. Browser automation is designed as a later execution layer, not as the core state owner.

## Goals

- Process fixed-format Google AI Studio storyboard output at scale.
- Support project-level planning metadata, batch-level text, and shot-level prompts.
- Identify shot types automatically:
  - Mode A: overlay/edit from a base image.
  - Mode B: new composition.
  - Key node video: generate a keyframe first, then use the keyframe plus I2V prompt in Jimeng.
- Provide a local visual workbench for status tracking, review, correction, and retries.
- Manage generated images, keyframes, videos, audio, subtitles, reports, and rendered outputs.
- Guarantee that final video, audio, and subtitles are aligned before export.
- Leave clear integration points for browser agents that operate Google AI Studio, Nano banana, and Jimeng.

## Non-Goals For MVP

- Fully unattended generation across all web tools.
- Automatic subjective quality judging for generated images and videos.
- Bypassing login, captcha, account limits, platform rate limits, or web-tool restrictions.
- Depending on unofficial APIs for Nano banana or Jimeng.

## Product Shape

The product is a local web workbench, not just a command-line script.

The workbench has:

- A project sidebar with current video, role card, storyboard batches, asset library, and export area.
- A central shot timeline with one card per shot.
- A detail panel for the selected shot, including timing, type, dialogue, prompts, dependencies, generated assets, and action buttons.
- A progress header showing total parsed shots, completed images, completed videos, missing assets, and render readiness.
- A task log showing parsing, import, validation, render, and later browser-agent activity.

This shape is required because the workflow includes many long-running, failure-prone, visually subjective tasks. The user needs to see status, identify missing or bad assets, replace individual shots, and render again without losing the whole project state.

## Input Model

The system accepts fixed-format Google AI Studio output with three levels.

### Project Level

Examples:

- Audio total duration: 538 seconds.
- Estimated regular images: about 359.
- Estimated key nodes: 10.
- Estimated batches: about 24.
- Batch size: 15 shots.
- Role card and global style lock.

### Batch Level

Examples:

- Batch number.
- Shot range, such as `第 1 张 — 第 15 张`.
- Narrative phase notes.
- Continuation hints such as asking the user to reply `继续`.

### Shot Level

Fields parsed per shot:

- Shot number.
- Start time.
- End time.
- Duration.
- Mode A or B.
- Key node marker.
- Key node type.
- Visual style note.
- Output form.
- Chinese and English dialogue when present.
- Image prompt.
- I2V prompt.
- Base image dependency.
- Keep unchanged instructions.
- Add new element instructions.

## Shot Types

### Mode B: New Composition

Data flow:

1. Use global role/style information plus the shot prompt.
2. Export as a Nano banana image task.
3. Import the generated image.
4. Review and mark complete.
5. Convert the image into a video segment of the target duration during render.

### Mode A: Overlay/Edit

Data flow:

1. Read the `Base Image` reference.
2. Wait until the referenced base image exists.
3. Export as a Nano banana edit task with base image, keep instructions, and add instructions.
4. Import the generated image.
5. Review and mark complete.
6. Convert the image into a video segment of the target duration during render.

The validator must flag Mode A shots whose base image is missing, ungenerated, or later than the dependent shot.

### Key Node Video

Confirmed strategy:

1. First generate a keyframe image using Nano banana.
2. Use the keyframe plus I2V prompt in Jimeng.
3. Import the generated video.
4. Validate and normalize the video to the shot duration during render.

This improves style consistency and keeps key nodes inside the same asset-management model as still images.

## Core Modules

### Frontend Workbench

Recommended stack: Vue and Vite, matching the current project direction.

Responsibilities:

- Create and open video projects.
- Import role cards, audio, planning text, and storyboard batches.
- Display the shot timeline and shot detail panel.
- Filter by batch, type, status, missing asset, failure, and dependency.
- Preview images, keyframes, videos, audio, and subtitles.
- Edit parsed fields when the parser needs human correction.
- Export prompt packages.
- Import generated assets through drag-and-drop or file picker.
- Trigger validation and rendering.
- Show validation and render reports.

### Backend Service

Recommended stack: Python and FastAPI.

Responsibilities:

- Parse storyboard text.
- Store project and shot data.
- Manage project files.
- Generate prompt packages.
- Match imported assets to shots.
- Generate subtitles.
- Validate timelines and dependencies.
- Run FFmpeg render jobs.
- Expose task and status APIs to the frontend.
- Provide extension points for browser agents.

### Browser Agent Layer

Recommended stack: Playwright.

Responsibilities:

- AI Studio Agent:
  - Open the current AI Studio conversation.
  - Detect completed storyboard batches.
  - Capture batch text.
  - Send continuation commands such as `继续` or `生成分镜`.
  - Pause on format errors, duplicate ranges, missing ranges, login issues, captcha, or account problems.

- Nano banana Agent:
  - Execute Mode B image tasks.
  - Execute Mode A overlay/edit tasks.
  - Generate keyframes for key node video shots.
  - Download files and bind them to shot IDs.
  - Pause on login, captcha, limits, obvious failures, or user review requests.

- Jimeng Agent:
  - Execute I2V tasks from keyframes and I2V prompts.
  - Download video results.
  - Record actual duration and file path.
  - Pause on login, captcha, limits, failed generation, or user review requests.

The browser agent layer does not own project truth. It only consumes workbench tasks and writes results back to the backend.

## Shot State Machine

Shot states:

- `parsed`
- `waiting_for_base_image`
- `image_pending`
- `image_generating`
- `image_ready`
- `image_needs_review`
- `image_failed`
- `keyframe_pending`
- `keyframe_ready`
- `video_pending`
- `video_generating`
- `video_ready`
- `video_needs_review`
- `video_failed`
- `approved`
- `in_render_plan`
- `rendered`

A failed or rejected shot should return only to the necessary step. The whole project must not need to restart because one image or video fails.

## MVP Features

### Project Creation

The user can create a video project and import:

- Video title.
- Role setting card.
- Audio file.
- Google AI Studio planning text.
- One or more storyboard batch texts.

### Storyboard Import And Parsing

The user can paste or import batch text. The parser extracts project metadata, batch metadata, and shot records.

Parser output can be reviewed and corrected in the UI.

### Shot Timeline

The workbench shows one card per shot with:

- Shot number.
- Time range.
- Type.
- Status.
- Missing asset flag.
- Dependency flag.
- Review flag.

### Prompt Package Export

The system exports separate task packages for:

- Nano banana regular image tasks.
- Nano banana keyframe tasks.
- Jimeng I2V tasks.

Each task includes shot ID, prompt, dependency files, expected output filename, and target duration.

### Asset Import And Matching

The user can drag generated images and videos into the asset library.

Matching rules:

- Prefer expected filenames such as `shot_001_image.png`, `shot_010_keyframe.png`, and `shot_010_video.mp4`.
- If filenames are ambiguous, ask the user to bind assets manually.
- Once bound, update shot state and validation status.

### Validation

The validator checks:

- Shot number gaps.
- Duplicate shot numbers.
- Time gaps.
- Time overlaps.
- Parsed shot count versus project planning estimate.
- Parsed key node count versus planning estimate.
- Missing image assets.
- Missing keyframes.
- Missing video assets.
- Mode A base image dependencies.
- Video duration mismatches.
- Subtitle timeline coverage.
- Final render readiness.

### Rendering

The renderer uses audio as the master timeline.

Rules:

- Final video duration must match the audio duration within a small tolerance.
- Image shots become video segments with the exact target duration.
- Video shots are normalized to target duration by trimming, holding the last frame, or controlled speed adjustment.
- If normalization would cause visible or timing problems, the shot is flagged for review.
- Rendering is blocked when required assets are missing or the timeline has unresolved gaps or overlaps.

Outputs:

- `final_clean.mp4`
- `final_with_subtitles.mp4`
- Render report.

### Subtitles

Subtitles are generated from each shot's dialogue field.

Supported MVP outputs:

- Chinese SRT.
- English SRT when English dialogue exists.
- Bilingual ASS subtitle file.
- Burned-in subtitle video.
- Clean video without burned-in subtitles.

Subtitle timing uses shot start and end times. Export is blocked if subtitle end time, video end time, and audio end time do not align.

## File Structure

Recommended project storage:

```text
video_projects/
  sleep-video-001/
    project.json
    shots.json
    audio/
      voiceover.wav
    prompts/
      nano_images/
      nano_keyframes/
      jimeng_i2v/
    assets/
      images/
      keyframes/
      videos/
    subtitles/
      zh.srt
      en.srt
      bilingual.ass
    renders/
      final_clean.mp4
      final_with_subtitles.mp4
    reports/
      validation.md
      missing_assets.md
      render_report.md
```

## Data Records

### Project Record

Project data includes:

- Project ID.
- Title.
- Audio path.
- Audio duration.
- Estimated image count.
- Estimated key node count.
- Estimated batch count.
- Batch size.
- Role card text.
- Global style lock.
- Created and updated timestamps.

### Shot Record

Shot data includes:

- Shot ID.
- Batch number.
- Start time.
- End time.
- Duration.
- Type.
- Mode.
- Dialogue Chinese.
- Dialogue English.
- Prompt image.
- Prompt I2V.
- Base image shot ID.
- Keep unchanged text.
- Add new element text.
- Expected files.
- Bound asset paths.
- Status.
- Review notes.
- Error message.

## Error Handling

Errors should be visible, local, and recoverable.

Examples:

- Parser cannot identify a time range: show the raw block and allow manual correction.
- Mode A references a missing image: mark as blocked by dependency.
- Imported asset cannot be matched: place in unassigned assets.
- Video is too short: hold last frame or request review, depending on configured threshold.
- Audio and storyboard duration differ: show difference and block final export until resolved.
- Browser agent hits captcha or login: pause the task and request manual intervention.

## Testing Strategy

MVP tests should cover:

- Parsing real storyboard samples with planning metadata, batch metadata, Mode A, Mode B, and key node blocks.
- Time parsing and duration calculation.
- Detection of gaps, overlaps, duplicate shots, and missing dependencies.
- Prompt package generation.
- Asset filename matching.
- SRT and ASS subtitle generation.
- Render-plan generation.
- FFmpeg command construction with mocked execution.
- API endpoints for project creation, storyboard import, asset binding, validation, and render triggering.

## Rollout Plan

### Phase 1: Local Workbench MVP

Build the stable local workflow:

1. Project creation.
2. Storyboard parser.
3. Shot database.
4. Timeline UI.
5. Prompt package export.
6. Asset import and matching.
7. Validation reports.
8. Subtitle generation.
9. Audio, video, and subtitle aligned rendering.

### Phase 2: AI Studio Agent

Add browser automation for AI Studio:

1. Detect current batch.
2. Capture batch text.
3. Continue generation.
4. Append parsed batches.
5. Pause on abnormal output.

### Phase 3: Nano banana And Jimeng Agents

Add browser automation for asset generation:

1. Generate images and keyframes in Nano banana.
2. Generate I2V videos in Jimeng.
3. Download and bind assets.
4. Recover from failures through the workbench.

## MVP Defaults

- Burned-in subtitles use a clear bottom-centered ASS style with Chinese above English when bilingual output is enabled.
- Short video assets are extended by holding the final frame by default. If the missing duration is large enough to look awkward, the validator flags the shot for review before final export.
- Long video assets are trimmed to the target shot duration by default. Later versions can add user-selected in/out points.
- Project state is stored in SQLite for reliable querying and status updates, while generated project artifacts are also written as JSON, subtitle, prompt, report, and media files for portability.
- The workbench should be built as a separate app area inside this repository rather than mixed into the existing Wealth Island product screens.

## Approved Direction

The approved direction is:

- Build a local web workbench as the main product surface.
- Include audio, visual, and subtitle alignment in MVP.
- Use browser agents as later execution plugins.
- For key node video shots, generate a Nano banana keyframe first, then use that keyframe with the I2V prompt in Jimeng.

---

## v1.0.0-beta.1 Status Addendum

The current released baseline is `v1.0.0-beta.1`.

Implemented beta capabilities include:

- Project creation and project listing.
- Storyboard import into persisted shot records.
- Asset upload, asset library listing, and asset binding for image, keyframe, and video paths.
- Nano Banana provider settings, image generation, and keyframe generation.
- Jimeng provider settings, mock/Jimeng video generation, and Jimeng REST job submit/poll workflow.
- Timeline reorder, timeline persistence, render plan generation, and render plan export.
- SRT/ASS subtitle generation utilities and media probing helpers.
- Vue workbench panels for provider settings, asset library, shot timeline, validation, render pipeline, timeline editing, and video jobs.

API responses use a standard envelope:

```json
{
  "success": true,
  "data": {}
}
```

Errors use:

```json
{
  "success": false,
  "error": {
    "code": "bad_request",
    "message": "Human-readable error message."
  }
}
```

Provider settings use a unified public schema across Nano Banana and Jimeng:

- `provider`
- `enabled`
- `configured`
- `credentials`, with boolean configured flags only
- non-secret fields such as `base_url`, `region`, `endpoint`, and `model`
- `updated_at`

Credential values can be submitted but must never be returned by API responses.

Beta Hardening Sprint 2 explicitly excludes new providers, new AI models, new API capabilities, new pages, new data tables, real Jimeng integration beyond the existing REST workflow shape, subtitles/dubbing product workflows, ffmpeg rendering, and new AI capabilities.

CI must pass backend tests, frontend tests, frontend build, and lint gates (`ruff check .` and `eslint .`).
