# Module B — Biometric Stress-Testing Suite

Maps to job responsibility: *"Stress-test facial/voice recognition systems and liveness
detection under adversarial conditions."*

| File | What it does |
|---|---|
| `face_spoof_tests.py` | Print, replay, mask, adversarial-patch, and morph attacks against a face embedding/match function. |
| `voice_adversarial_generator.py` | Pitch-shift, replay, splice, and adversarial-noise attacks against a speaker embedding. |
| `liveness_bypass_tests.py` | Static-photo, looped-video, texture-spoof, and challenge-response bypass simulations against a motion/periodicity-based liveness heuristic. |
| `stress_test_dashboard.py` | Runs the full battery and renders `docs/stress_test_report.json` + `docs/stress_test_dashboard.html`. |

## Run it

```bash
python3 biometric-stress-tests/stress_test_dashboard.py
open docs/stress_test_dashboard.html   # or just open the file in a browser
```

## Why the default vulnerability scores are high (by design)

The bundled `default_embedder` / `simple_voice_embedding` / liveness heuristic are
intentionally **naive, threshold-based baselines** (HOG features, raw cosine similarity,
a fixed 0.85/0.9 match threshold, a simple motion+periodicity liveness rule) — not a
production biometric SDK. Running the attack battery against them exposes exactly the
kind of miscalibration a real Biometric/Deepfake Defense analyst is hired to catch:
*naively-tuned thresholds let structurally-similar spoofs through.*

This is the intended workflow:
1. Run the battery → get a vulnerability score per subsystem.
2. Feed the findings into `ai-safety-evaluation/guardrail_scoring.py` to recommend a
   better-calibrated threshold.
3. Re-run the battery against the new threshold to confirm the vulnerability score drops.

See `docs/ai-safety-evaluation-methodology.md` for that full loop, and swap in a real
FaceNet/ArcFace/d-vector model by replacing `Embedder` — the attack/scoring code is
model-agnostic.
