# Coffee Commercial Demo

This demo project is a compact validation scenario for `v1.0.0-beta.1`. It uses only existing AI Video Workbench capabilities and does not require any new provider, model, API, page, or table.

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
| 1 | `coffee-shot-001.png` | `data/uploads/1/generated/keyframes/coffee-shot-001.png` | `nano_banana` | Warm kitchen counter with steaming coffee cup. |
| 2 | `coffee-shot-002-keyframe.png` | `data/uploads/1/generated/keyframes/coffee-shot-002-keyframe.png` | `nano_banana` | Macro coffee pour-over keyframe with beans. |
| 3 | `coffee-shot-003.png` | `data/uploads/1/generated/keyframes/coffee-shot-003.png` | `nano_banana` | Premium quiet coffee ritual end frame. |

## Videos

| Shot | Asset Name | Path | Source | Expected Status |
| --- | --- | --- | --- | --- |
| 1 | `coffee-shot-001.mp4` | `data/uploads/1/generated/videos/coffee-shot-001.mp4` | `mock` or `jimeng` | `video_ready` |
| 2 | `coffee-shot-002.mp4` | `data/uploads/1/generated/videos/coffee-shot-002.mp4` | `jimeng` | `video_ready` |
| 3 | `coffee-shot-003.mp4` | `data/uploads/1/generated/videos/coffee-shot-003.mp4` | `mock` or `jimeng` | `video_ready` |

## Timeline

| Order | Shot | Duration | Video Path |
| --- | --- | --- | --- |
| 1 | 1 | 4s | `data/uploads/1/generated/videos/coffee-shot-001.mp4` |
| 2 | 2 | 4s | `data/uploads/1/generated/videos/coffee-shot-002.mp4` |
| 3 | 3 | 4s | `data/uploads/1/generated/videos/coffee-shot-003.mp4` |

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
      "video_path": "data/uploads/1/generated/videos/coffee-shot-001.mp4",
      "duration_seconds": 4.0
    },
    {
      "shot_id": 2,
      "video_path": "data/uploads/1/generated/videos/coffee-shot-002.mp4",
      "duration_seconds": 4.0
    },
    {
      "shot_id": 3,
      "video_path": "data/uploads/1/generated/videos/coffee-shot-003.mp4",
      "duration_seconds": 4.0
    }
  ]
}
```

## Demo Flow

1. Create the project with title `Coffee Commercial Demo`.
2. Import the three-shot storyboard.
3. Configure Nano Banana and Jimeng provider settings.
4. Generate or bind the three keyframes.
5. Generate or bind the three videos.
6. Confirm timeline order is 1, 2, 3.
7. Generate Render Plan.
8. Export Render Plan.
9. Confirm the API response uses the standard `{ "success": true, "data": ... }` envelope.
