"""
guardrail_scoring.py
------------------------
AI safety guardrail scoring metrics.

Given a classifier's scores on labeled data (e.g. the synthetic-media
classifier from artifact-detection/, or the biometric match scores from
biometric-stress-tests/), sweeps the decision threshold and reports the
standard guardrail trade-off metrics: precision, recall, F1, false-positive
rate, false-negative rate — then recommends a threshold under an explicit
policy (e.g. "maximize F1" or "minimize false-negative rate subject to
FPR <= 5%", the latter being the typical policy for a safety-critical
deepfake/spoof gate where missing a real attack is costlier than a false
alarm).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

import numpy as np


@dataclass
class ThresholdMetrics:
    threshold: float
    precision: float
    recall: float
    f1: float
    false_positive_rate: float
    false_negative_rate: float
    accuracy: float


def sweep_thresholds(y_true: Sequence[int], y_scores: Sequence[float], n_steps: int = 41) -> List[ThresholdMetrics]:
    y_true = np.asarray(y_true)
    y_scores = np.asarray(y_scores)
    results = []
    for t in np.linspace(0.0, 1.0, n_steps):
        y_pred = (y_scores >= t).astype(int)
        tp = int(np.sum((y_pred == 1) & (y_true == 1)))
        fp = int(np.sum((y_pred == 1) & (y_true == 0)))
        fn = int(np.sum((y_pred == 0) & (y_true == 1)))
        tn = int(np.sum((y_pred == 0) & (y_true == 0)))

        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        fpr = fp / (fp + tn) if (fp + tn) else 0.0
        fnr = fn / (fn + tp) if (fn + tp) else 0.0
        acc = (tp + tn) / len(y_true) if len(y_true) else 0.0

        results.append(ThresholdMetrics(round(float(t), 3), precision, recall, f1, fpr, fnr, acc))
    return results


def recommend_threshold(
    metrics: List[ThresholdMetrics], policy: str = "max_f1", max_fpr: float = 0.05
) -> ThresholdMetrics:
    """policy:
      - 'max_f1'                     : maximize F1 score
      - 'min_fnr_subject_to_fpr'     : minimize false-negative rate subject to FPR <= max_fpr
                                        (recommended default for safety-critical deepfake gates,
                                        since a missed deepfake/spoof is typically costlier than
                                        a false alarm that a human reviewer clears)
    """
    if policy == "min_fnr_subject_to_fpr":
        candidates = [m for m in metrics if m.false_positive_rate <= max_fpr]
        pool = candidates if candidates else metrics
        return min(pool, key=lambda m: m.false_negative_rate)
    return max(metrics, key=lambda m: m.f1)


if __name__ == "__main__":
    rng = np.random.default_rng(0)
    y_true = np.array([0] * 100 + [1] * 100)
    y_scores = np.concatenate([
        rng.beta(2, 6, 100),   # real -> low scores
        rng.beta(6, 2, 100),   # synthetic -> high scores
    ])
    metrics = sweep_thresholds(y_true, y_scores)
    best_f1 = recommend_threshold(metrics, policy="max_f1")
    best_safety = recommend_threshold(metrics, policy="min_fnr_subject_to_fpr", max_fpr=0.05)

    print("Best by max F1        :", best_f1)
    print("Best by safety policy  (FPR<=5%):", best_safety)
