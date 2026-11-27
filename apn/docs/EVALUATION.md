# Evaluation

The fixed dataset is a 27-second composed four-stage supermarket story. CAM-02,
CAM-03, and CAM-04 are contiguous segments from one source video. CAM-01 is a
independent source clip. Therefore results validate integration, not synchronized CCTV
cross-camera accuracy.

Measured pipeline runs:

| System | Observations | Time | Sampled-frame throughput |
|---|---:|---:|---:|
| HOG + centroid + HSV | 200 | 15.207 s | 3.37–7.26 FPS |
| YOLO11n + ByteTrack + HSV | 664 | 92.266 s | 2.55–3.71 FPS |

Two reference handoffs have known same-character chronology. Autonomous matching
now ranks every eligible target-camera track rather than receiving target IDs.
With the lightweight HSV descriptor it does not recover either known reference
link. All three selected links remain ambiguous, so strict automated precision is
undefined and recall is 0. Including ambiguous review candidates still gives 0
precision/recall against the references. This useful negative result shows that
uncertainty prevents false automatic merges, but stronger re-identification
features and labelled data are required. The CAM-01 link remains unknown.

IDF1 and ID-switch counts are deliberately not reported: dense ground truth is
not available. Reporting those values would imply evidence the dataset does not
contain. See `eval/results.json` for machine-readable output and limitations.

The current CPU does not reach half real-time at 960-pixel YOLO inference.
Apple MPS/GPU acceleration, smaller inference size, or increased frame skipping
is required for interactive live throughput. Offline deterministic replay is
fully supported.
