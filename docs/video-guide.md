# Video guide

> Author: Bahae Eddine HALIM <https://www.linkedin.com/in/halimbahae/>

Recon works on stills, so GeoWeb turns a clip into a small set of
**representative frames** first — then you analyse the one that shows the most.
This keeps evidence (signs, plates, landmarks) readable while keeping the run
cheap.

## The sampler

`video/frames.py` (OpenCV + numpy, declared as PEP-723 deps):

```bash
uv run video/frames.py clip.mp4 --out-dir frames
uv run video/frames.py clip.mp4 --out-dir frames --max 24 --hamming 3 --scene 16
```

| flag | default | meaning |
| --- | --- | --- |
| `--max` | `12` | cap on exported frames |
| `--hamming` | `3` | max 64-bit dHash distance for two frames to count as duplicates |
| `--scene` | `16` | scene-change threshold (mean abs diff) |

Pipeline inside the sampler:

1. **Uniform pass** over the whole timeline (so you never miss a long tail).
2. **Scene changes** broken out (cuts and hard pans).
3. **dHash dedupe** — near-identical frames dropped by Hamming distance.
4. **Even trim** to `--max`, keeping spread across the clip.

Output:

```
frames/frame_000000.jpg … frame_000011.jpg   distinct frames
frames/contact_sheet.jpg                     one-page overview
frames/samples.json   [{index, t_sec, file, ts}]
frames/video.json     {path, width, height, fps, n_frames, duration}
```

## In the console

Drop a clip on the dropzone (or `POST /api/sessions` with `photo=@clip.mp4`).
The session becomes `kind: video` and the **Frames** tab fills in:

- a **contact sheet** across the top,
- a **frame grid** with timestamps and a "use this frame" button per cell,
- a **re-extract** action to re-run the sampler with new settings.

Pick a frame → **Run recon** analyses exactly that still, and everything else
(metadata, OCR, reverse search, priors, the map, finishing) behaves like a photo.

## Why this shape

- **One frame = one clean evidence set.** No motion blur averages, no giant
  contact sheets to eyeball, no ambiguity about which moment a clue came from.
- **Cheap.** You analyse a still, not every frame.
- **Faithful.** The chosen frame keeps its own EXIF-adjacent context and is
  stored as a real file you can re-open later.

## API

```bash
S=$(curl -sX POST $BASE/api/sessions -F photo=@clip.mp4 | jq -r .name)
curl -s $BASE/api/session/$S/frames | jq '.count, .samples[].file'
curl -sX POST $BASE/api/session/$S/recon \
     -H 'content-type: application/json' -d '{"frame":"frame_000075.jpg","no_ml":true}'
```
