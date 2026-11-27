# Phase 0 — Footage discovery

## Scope

The APN demo configuration uses every distinct available camera clip:

1. `cam_01_entrance.mp4` — entrance and front-of-store view.
2. `cam_02_main_aisle.mp4` — main aisle view.
3. `cam_03_service_counter.mp4` — service-counter view.
4. `cam_04_checkout.mp4` — checkout view.

The two top-level MP4 files are preserved as source assets rather than registered
as additional cameras. `Shoppers_entering_supermarket…mp4` is byte-for-byte
identical to CAM-01. `People_shopping_in_supermarket…mp4` is the original source
from which the short CAM-02 through CAM-04 scenario clips were produced.
Registering these originals as cameras would duplicate evidence and produce false
camera and person counts.

## Measured properties

| Camera | Resolution | FPS | Frames | Duration | Codec | HOG discovery result |
|---|---:|---:|---:|---:|---|---|
| CAM-01 | 1280×720 | 24 | 360 | 15.000 s | H.264 | people detected in 24/24 sampled frames; max 6 |
| CAM-02 | 1280×720 | 24 | 95 | 3.958 s | H.264 | people detected in 24/24 sampled frames; max 3 |
| CAM-03 | 1280×720 | 24 | 72 | 3.000 s | H.264 | people detected in 24/24 sampled frames; max 3 |
| CAM-04 | 1280×720 | 24 | 121 | 5.042 s | H.264 | people detected in 22/24 sampled frames; max 2 |

The HOG counts are a discovery heuristic, not ground truth or a final detector evaluation.

## Visual findings

- CAM-01 clearly shows the supermarket entrance.
- CAM-02 clearly shows a main aisle.
- CAM-03 clearly shows a service counter.
- CAM-04 clearly shows checkout.
- A red-clothed person appears across the sequence, making the clips suitable for an integration story.
- The cameras are distinct viewpoints and do not appear to overlap directly.
- CAM-02 and CAM-03 share very similar overall scene colour statistics, consistent with the same store environment, but this does not establish physical adjacency.
- The short clips appear to be sequential segments of a composed scenario rather than simultaneous camera recordings.

Frame-level matching against the original 15-second store video establishes the
exact source relationship:

| Derived view | Source frames | Source time |
|---|---:|---:|
| CAM-02 | 72–166 | 3.000–6.917 s |
| CAM-03 | 167–238 | 6.958–9.917 s |
| CAM-04 | 239–359 | 9.958–14.958 s |

These three clips are contiguous segments, with a one-frame boundary between
each. CAM-01 comes from an independent entrance video. Consequently, only
the CAM-01 → CAM-02 transition is manually composed; CAM-02 → CAM-03 → CAM-04
preserves the exact order of the source asset.

## Proposed configuration

- Timeline mode: `COMPOSED`.
- Topology: `CAM-01 ↔ CAM-02 ↔ CAM-03 ↔ CAM-04`.
- Store-clock offsets: 0 s, 15 s, 18.958 s, and 21.958 s.
- CAM-01 role: Entrance.
- CAM-02 role: Main Aisle.
- CAM-03 role: Service Counter.
- CAM-04 role: Checkout.

The UI and evaluation must label results from this arrangement as **COMPOSED TIMELINE — clips aligned manually**. Cross-camera outcomes from these clips are an integration test, not a tracking benchmark.

## Dataset decision

The user delegated footage interpretation and topology selection to the build.
The four-view sequence above is therefore the locked Phase 0 validation dataset.
It will be used throughout development for integration and regression testing.
It must not be represented as synchronized real CCTV or used to claim real-world
cross-camera accuracy.
