# Deepfake Analyst Capability Demonstration

This document maps every responsibility in the *Deepfake Defense & Digital Forensics
Analyst – Intermediate (AI Community)* job posting to the concrete, runnable code in this
repository, so a reviewer can verify each claim in minutes.

| Job responsibility | Toolkit evidence | How to verify |
|---|---|---|
| Detect synthetic media artifacts across image/video/audio | `artifact-detection/` (fingerprint extractor, frame scanner, spectrogram detector, classifier) | `artifact-detection/README.md` Quickstart — trains a real classifier and prints accuracy/ROC-AUC on locally generated data |
| Stress-test facial/voice recognition + liveness | `biometric-stress-tests/` (5 face attacks, 4 voice attacks, 4 liveness bypasses) | `python3 biometric-stress-tests/stress_test_dashboard.py` → `docs/stress_test_dashboard.html` |
| Produce forensic reports of manipulation markers | `forensic-reporting/` (Markdown, JSON, PDF, chain-of-custody, evidence packaging) | `docs/sample-reports/` contains real generated report artifacts, not mockups |
| Evaluate AI models / refine safety guardrails | `ai-safety-evaluation/` (threshold sweeps, robustness tests, evasion shield harness, drift detection) | `docs/ai-safety-evaluation-methodology.md` + run any script in that folder |
| Contribute to deepfake detection model training | `artifact-detection/classifier/synthetic_classifier.py` + `datasets/generators/synthetic_data_generator.py` | Retrain from scratch: `python3 datasets/generators/synthetic_data_generator.py && python3 artifact-detection/classifier/synthetic_classifier.py` |
| AI Community annotation/evaluation workflow | `annotation-simulator/` (multi-annotator simulation, Fleiss' Kappa, offline labeling UI) | `python3 annotation-simulator/annotation_workflow_simulator.py` |
| Qualification exam requirement | `annotation-simulator/qualification_exam_simulator.py` | Domain-knowledge exam bank across all 6 modules, pass/fail scoring |
| Native/fluent language proficiency requirement | `annotation-simulator/native_language_evaluation_module.py` | Language-ID cross-check + fluency-mismatch flagging harness |
| Global collaboration / AI-safety mission alignment | See "Alignment with TELUS Digital AI Community" in the main README | — |

## What is real vs. explicitly simulated, and why

This repository is a **portfolio/demonstration project**, built without a GPU, without a
licensed real-face dataset, and without production biometric SDKs. Every module is built
so that:

1. **The methodology is real and runnable.** Every script executes end-to-end and produces
   genuine, reproducible numbers (not hard-coded "97% accuracy" claims) — see each module's
   README for the exact command and expected output shape.
2. **The data is synthetic-by-design.** `datasets/generators/synthetic_data_generator.py`
   procedurally creates a real-vs-fake dataset locally, avoiding any licensing, privacy, or
   scraped-data concerns while still exercising every detector honestly.
3. **Swap-in points are explicit.** Every place a production system would plug in a real
   trained CNN/ViT, a real face/voice embedding model, or a real biometric liveness SDK is
   marked with a `# SWAP-IN POINT` comment and documented (e.g.
   `artifact-detection/classifier/synthetic_classifier.py`,
   `biometric-stress-tests/face_spoof_tests.py`).

This is deliberate: a hiring reviewer can run every command in this repo and see the exact
numbers reported here, rather than trusting unverifiable claims.

## Suggested review path (10 minutes)

```bash
python3 datasets/generators/synthetic_data_generator.py --out datasets/synthetic_media --n 150
python3 artifact-detection/classifier/synthetic_classifier.py
python3 biometric-stress-tests/stress_test_dashboard.py
python3 forensic-reporting/report_generator.py --llm
python3 ai-safety-evaluation/model_drift_detection.py
python3 annotation-simulator/annotation_workflow_simulator.py
pytest tests/ -q
```
