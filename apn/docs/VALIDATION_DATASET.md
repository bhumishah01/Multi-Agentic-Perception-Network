# APN validation footage contract

## Purpose

These clips are the fixed development dataset for building and repeatedly
validating APN. They form a controlled multi-camera replay, not synchronized production CCTV
capture. They are suitable for pipeline integration, causal-message, handoff,
case-building, security, API, and interface tests. They are not sufficient for
claims about deployment accuracy.

## Canonical four-stage journey

```text
CAM-01 Entrance
  → CAM-02 Main Aisle
  → CAM-03 Service Counter
  → CAM-04 Checkout
```

The visually dominant red-clothed character is the target entity used by the
demo scenario. The system may propose that the person in CAM-01 continues into
CAM-02, but this is a manually composed handoff and must retain uncertainty. The
CAM-02, CAM-03, and CAM-04 clips are contiguous source segments containing the
same red-clothed character.

## Expected observable facts

### CAM-01 — Entrance

- Multiple people enter and move through the entrance area.
- Shopping carts and entrance doors are visible.
- The red-clothed target moves from the entrance toward the store interior.
- The view is busy and contains occlusion, making it useful for detector and
  local-tracker validation.

### CAM-02 — Main Aisle

- The red-clothed target moves along the aisle, generally away from the camera.
- Another person in yellow is present near the shelves.
- Shelf proximity and aisle traversal support dwell, movement, and ambiguity
  tests, but must never be labelled as theft.

### CAM-03 — Service Counter

- The red-clothed target enters from the right side and approaches/crosses the
  service-counter area.
- Several other people remain around the counter.
- This supports zone entry, counter congestion, and candidate-handoff tests.

### CAM-04 — Checkout

- The red-clothed target approaches the checkout from the lower/foreground area.
- Another customer later approaches with a basket.
- The scene supports checkout occupancy and queue-rule integration tests.

## Timeline

| Camera | Store-clock start | Duration | Relationship |
|---|---:|---:|---|
| CAM-01 | 0.000 s | 15.000 s | independent entrance clip |
| CAM-02 | 15.000 s | 3.958 s | source frames 72–166 |
| CAM-03 | 18.958 s | 3.000 s | source frames 167–238 |
| CAM-04 | 21.958 s | 5.042 s | source frames 239–359 |

## Required truth labels

Every product surface and evaluation report must display or preserve:

- `mode = COMPOSED`
- `COMPOSED TIMELINE — clips aligned manually`
- CAM-01 → CAM-02 is an integration-test association, not ground truth.
- CAM-02 → CAM-03 → CAM-04 preserves source chronology but simulates camera
  transitions by cutting one video into distinct views.
- Heuristic detector and handoff scores are scores, not probabilities.
- No biometric or facial-recognition claim is permitted.

## Validation use

The footage will be reused for deterministic regression tests. As stronger
detectors and trackers are introduced, versioned pipeline outputs should be
compared against hand-labelled track and zone events rather than silently
changing the expected scenario.
