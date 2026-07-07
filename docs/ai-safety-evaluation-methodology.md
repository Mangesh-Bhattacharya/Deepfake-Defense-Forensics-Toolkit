# AI Safety Evaluation Methodology

This document describes the evaluation loop implemented across
`ai-safety-evaluation/` and how it connects to `artifact-detection/` and
`biometric-stress-tests/`.

## 1. Threshold calibration (`guardrail_scoring.py`)

Given labeled scores, sweep the decision threshold from 0 to 1 and compute precision,
recall, F1, false-positive rate (FPR), and false-negative rate (FNR) at each point.

Two selection policies are implemented:
- **max_f1** — balances precision and recall equally.
- **min_fnr_subject_to_fpr** (recommended for safety-critical gates) — minimizes missed
  detections (false negatives) subject to a maximum tolerable false-alarm rate. This
  reflects the real cost asymmetry in deepfake/spoof detection: a missed attack is
  typically far costlier than a false alarm a human reviewer can clear.

## 2. Robustness testing (`model_robustness_evaluator.py`)

Methodology follows Hendrycks & Dietterich (2019) "Benchmarking Neural Network Robustness
to Common Corruptions and Perturbations": measure accuracy under a battery of realistic,
non-adversarial corruptions (JPEG re-compression, Gaussian noise, resize round-trip,
brightness shift) that content routinely undergoes in the wild (e.g. re-upload through a
social platform). Accuracy drop per corruption type quantifies where the model is fragile.

## 3. Adversarial shield testing (`synthetic_media_shield_harness.py`)

Simulates a real content-safety gate's ALLOW/REVIEW/BLOCK decision and specifically tests
whether an adversary who *knows* the classifier exists can craft a mild perturbation
(blur + low-amplitude noise) to reduce the classifier's confidence below the block
threshold — i.e., an evasion attack, distinct from the corruption robustness test above
(which uses non-adversarial, incidental corruptions).

## 4. Drift detection (`model_drift_detection.py`)

Population Stability Index (PSI) is the industry-standard metric for monitoring whether a
live feature distribution has shifted from the distribution a model was trained/validated
on:

| PSI | Interpretation |
|---|---|
| < 0.10 | stable, no action needed |
| 0.10 – 0.25 | moderate shift — investigate |
| > 0.25 | major shift — retrain/recalibrate |

Cross-checked with a per-feature two-sample Kolmogorov-Smirnov test for statistical
significance. In production, run this weekly/monthly against a rolling window of new
content to catch when new deepfake generators have shifted the artifact distribution
enough that the classifier and its calibrated threshold need to be refreshed.

## 5. How the four pieces fit together

```
new deepfake generator emerges in the wild
        │
        ▼
model_drift_detection.py flags PSI > 0.25 on incoming traffic
        │
        ▼
collect labeled samples of the new pattern → retrain classifier (artifact-detection/classifier/)
        │
        ▼
model_robustness_evaluator.py + synthetic_media_shield_harness.py
   re-validate the retrained model isn't fragile / evadable
        │
        ▼
guardrail_scoring.py re-calibrates the production threshold on the new model's scores
        │
        ▼
biometric-stress-tests/stress_test_dashboard.py re-run to confirm vulnerability score
   has not regressed for any downstream biometric subsystem sharing the guardrail
```

This closes the loop the job posting describes as *"evaluate AI model performance and
contribute to refining safety guardrails."*
