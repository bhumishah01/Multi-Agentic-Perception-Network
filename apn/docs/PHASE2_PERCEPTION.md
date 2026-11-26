# Phase 2 — Perception pipeline

## Delivered

- Selectable `yolo` and `hog` detector paths.
- YOLO11n person detection with Ultralytics ByteTrack.
- HOG plus centroid association retained as the comparison baseline.
- Structured, validated observations for every tracked detection.
- Source and composed store timestamps.
- Bounding boxes and foot points.
- Zone assignment with polygon support and named-view fallback.
- Crop references and persisted anonymous HSV appearance embeddings.
- Blur, overlap-based occlusion estimate, and crop-size quality fields.
- One hash-chained `observation` message per output observation.
- JSON observation output and performance summary.
- Non-destructive overlay renderer; boxes are not burned into source footage.

Ultralytics is AGPL-3.0 licensed. This must be reviewed before distribution or
hosted/commercial deployment.

## Measured four-camera run

### HOG baseline (`--every 8`)

- 200 observations and 200 verified ledger messages.
- 15.207 seconds total.
- Sampled-frame processing: 3.374–7.262 FPS depending on camera.

### YOLO11n + ByteTrack (`--every 4`, 960 px inference setting)

- 664 observations and 664 verified ledger messages.
- 92.266 seconds total, including first-run model/tracker setup overhead.
- Sampled-frame processing: 2.546–3.705 FPS depending on camera.

This CPU-only machine does not meet the target of half real-time at the current
960 px setting. Use Apple MPS/GPU acceleration, a smaller inference size, or a
larger frame-skip for interactive replay. The present measured output is valid
for offline deterministic processing.

## Honest limitations

- HSV histograms are the baseline descriptor, not the preferred OSNet embedding.
- No face or biometric recognition is performed.
- Floor coordinates, velocity, and heading remain null until Phase 3 calibration.
- Camera-name zones are fallbacks until zone polygons are drawn in Phase 3.
- The footage is composed and cannot establish real cross-camera accuracy.
