# Module D — AI Safety Guardrail Evaluation Tools

Maps to job responsibility: *"Evaluate AI model performance and contribute to refining
safety guardrails."*

| File | What it does |
|---|---|
| `guardrail_scoring.py` | Sweeps decision thresholds, reports precision/recall/F1/FPR/FNR, and recommends a threshold under an explicit safety policy (e.g. minimize false negatives subject to FPR ≤ 5%). |
| `model_robustness_evaluator.py` | Runs Hendrycks & Dietterich-style corruption tests (JPEG re-compression, noise, resize round-trip, brightness) against the classifier and measures accuracy drop. |
| `synthetic_media_shield_harness.py` | Simulates an ALLOW/REVIEW/BLOCK content-safety gate and measures how often an adversarial evasion perturbation bypasses it. |
| `model_drift_detection.py` | Population Stability Index + Kolmogorov-Smirnov drift detection between a baseline feature distribution and a new batch — flags when the classifier needs retraining. |

## Run it

```bash
python3 artifact-detection/classifier/synthetic_classifier.py   # train first
python3 ai-safety-evaluation/guardrail_scoring.py
python3 ai-safety-evaluation/model_robustness_evaluator.py
python3 ai-safety-evaluation/synthetic_media_shield_harness.py
python3 ai-safety-evaluation/model_drift_detection.py
```

Full methodology write-up: [`docs/ai-safety-evaluation-methodology.md`](../docs/ai-safety-evaluation-methodology.md).
