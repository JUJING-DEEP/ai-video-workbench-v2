# Coffee Commercial Demo

This demo project is a compact validation scenario for `v1.0.0-rc.1` GA readiness. It uses only existing AI Video Workbench capabilities and does not require any new provider, model, API, page, or table.

Machine-readable fixture:

```text
demo/coffee-commercial.json
```

Use the fixture by starting the existing backend and frontend, opening
`/video-workbench`, and clicking **Import Demo**. The UI creates the project,
imports `storyboard_text`, registers the local demo assets, binds shot asset
paths, and saves the fixture timeline using existing APIs.

The fixture media files live in:

```text
demo/assets/
demo/audio/coffee-commercial-12s.wav
```

## Project

- Title: Coffee Commercial Demo
- Slug: coffee-commercial-demo
- Goal: Demonstrate a 12-second product-style coffee spot with three shots, generated keyframes, generated or bound video clips, timeline ordering, and render-plan export.
- Audio: `demo/audio/coffee-commercial-12s.wav`
- Duration: 12 seconds

## Shots

| Shot | Time | Mode | Kind | Dialogue | Image Prompt | I2V Prompt |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 0:00-0:04 | B | image | Fresh coffee, fresh morning. | Warm kitchen counter, ceramic cup, morning light, steam rising from black coffee. | Slow push-in toward steaming cup, soft morning highlights. |
| 2 | 0:04-0:08 | KEY_NODE | key_node_video | Roasted rich, poured smooth. | Close macro shot of coffee beans beside a glass pour-over brewer. | Coffee pours into a glass server, rich amber stream, gentle camera drift. |
| 3 | 0:08-0:12 | B | image | Your quiet ritual, ready now. | Finished cup beside notebook and spoon, clean premium commercial composition. | Subtle steam movement, calm end-card hold. |

## Keyframes

| Shot | Asset Name | Path | Source | Prompt |
| --- | --- | --- | --- | --- |
| 1 | `coffee-shot-001-keyframe.png` | `demo/assets/coffee-shot-001-keyframe.png` | `demo` | Warm kitchen counter with steaming coffee cup keyframe. |
| 2 | `coffee-shot-002-keyframe.png` | `demo/assets/coffee-shot-002-keyframe.png` | `demo` | Macro coffee pour-over keyframe with beans. |
| 3 | `coffee-shot-003-keyframe.png` | `demo/assets/coffee-shot-003-keyframe.png` | `demo` | Premium quiet coffee ritual end keyframe. |

## Videos

| Shot | Asset Name | Path | Source | Expected Status |
| --- | --- | --- | --- | --- |
| 1 | `coffee-shot-001.mp4` | `demo/assets/coffee-shot-001.mp4` | `demo` | `video_ready` |
| 2 | `coffee-shot-002.mp4` | `demo/assets/coffee-shot-002.mp4` | `demo` | `video_ready` |
| 3 | `coffee-shot-003.mp4` | `demo/assets/coffee-shot-003.mp4` | `demo` | `video_ready` |

## Timeline

| Order | Shot | Duration | Video Path |
| --- | --- | --- | --- |
| 1 | 1 | 4s | `demo/assets/coffee-shot-001.mp4` |
| 2 | 2 | 4s | `demo/assets/coffee-shot-002.mp4` |
| 3 | 3 | 4s | `demo/assets/coffee-shot-003.mp4` |

Validation expectations:

- No duplicate shot IDs.
- No timing gaps or overlaps.
- Every timeline item has a video path.
- Render readiness is true after the three videos are bound.

## Render Plan

Expected export path:

```text
data/exports/1/render-plan.json
```

Expected render-plan shape:

```json
{
  "project_id": 1,
  "shots": [
    {
      "shot_id": 1,
      "video_path": "demo/assets/coffee-shot-001.mp4",
      "duration_seconds": 4.0
    },
    {
      "shot_id": 2,
      "video_path": "demo/assets/coffee-shot-002.mp4",
      "duration_seconds": 4.0
    },
    {
      "shot_id": 3,
      "video_path": "demo/assets/coffee-shot-003.mp4",
      "duration_seconds": 4.0
    }
  ]
}
```

## Demo Flow

1. Start backend and frontend.
2. Open `http://127.0.0.1:5173/video-workbench`.
3. Click **Import Demo**.
4. Confirm Storyboard contains shots 1, 2, and 3.
5. Confirm Asset Library contains demo image, keyframe, and video assets.
6. Confirm Timeline order is 1, 2, 3.
7. Optional: move Shot 2 up and click **Save Timeline**.
8. Click **Generate Render Plan**.
9. Click **Export Render Plan**.
10. Confirm `render-plan.json` uses the same order as the saved Timeline.
