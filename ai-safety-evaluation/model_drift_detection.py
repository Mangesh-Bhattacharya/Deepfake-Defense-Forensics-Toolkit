"""
model_drift_detection.py
----------------------------
Model / data drift detection.

Compares the feature distribution of a new incoming batch of media against a
stored baseline (e.g. the distribution the classifier was trained/validated
on) using:
  1. Population Stability Index (PSI) per feature — the industry-standard
     metric for scorecard/model monitoring (PSI < 0.1 = no significant
     shift, 0.1-0.25 = moderate shift/investigate, > 0.25 = major shift/retrain).
  2. Kolmogorov-Smirnov two-sample test per feature as a statistical
     significance cross-check.

Use this periodically in production to know when the synthetic-media
classifier or biometric embeddings need re-training/re-calibration because
new deepfake generators have shifted the artifact distribution.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import List

import numpy as np
from scipy import stats

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "artifact-detection", "image"))
from gan_fingerprint import extract_fingerprint  # noqa: E402


@dataclass
class DriftResult:
    feature: str
    psi: float
    ks_statistic: float
    ks_pvalue: float
    status: str  # "stable" | "moderate_shift" | "major_shift"


def compute_psi(baseline: np.ndarray, current: np.ndarray, n_bins: int = 10) -> float:
    edges = np.quantile(baseline, np.linspace(0, 1, n_bins + 1))
    edges[0], edges[-1] = -np.inf, np.inf
    edges = np.unique(edges)
    if len(edges) < 2:
        return 0.0

    base_counts, _ = np.histogram(baseline, bins=edges)
    curr_counts, _ = np.histogram(current, bins=edges)

    base_pct = np.clip(base_counts / max(len(baseline), 1), 1e-4, None)
    curr_pct = np.clip(curr_counts / max(len(current), 1), 1e-4, None)

    return float(np.sum((curr_pct - base_pct) * np.log(curr_pct / base_pct)))


def detect_drift(
    baseline_features: np.ndarray, current_features: np.ndarray, feature_names: List[str]
) -> List[DriftResult]:
    results = []
    for i, name in enumerate(feature_names):
        base_col = baseline_features[:, i]
        curr_col = current_features[:, i]
        psi = compute_psi(base_col, curr_col)
        ks_stat, ks_p = stats.ks_2samp(base_col, curr_col)

        if psi < 0.1:
            status = "stable"
        elif psi < 0.25:
            status = "moderate_shift"
        else:
            status = "major_shift"

        results.append(DriftResult(name, round(psi, 4), round(float(ks_stat), 4), round(float(ks_p), 4), status))
    return results


if __name__ == "__main__":
    import cv2
    import glob

    data_dir = os.path.join(os.path.dirname(__file__), "..", "datasets", "synthetic_media")
    files = sorted(glob.glob(os.path.join(data_dir, "real_*.png")))
    if not files:
        print("Generate the dataset first: python3 datasets/generators/synthetic_data_generator.py")
        sys.exit(0)

    imgs = [cv2.cvtColor(cv2.imread(f), cv2.COLOR_BGR2RGB) for f in files]
    features = np.stack([extract_fingerprint(im).features for im in imgs])
    names = extract_fingerprint(imgs[0]).feature_names

    half = len(features) // 2
    baseline = features[:half]

    # simulate a "drifted" new batch: brighten images to shift the noise/edge statistics
    drifted_imgs = [np.clip(im.astype(np.int32) + 60, 0, 255).astype(np.uint8) for im in imgs[half:]]
    drifted_features = np.stack([extract_fingerprint(im).features for im in drifted_imgs])

    for r in detect_drift(baseline, drifted_features, names):
        print(f"{r.feature:26s} PSI={r.psi:6.3f}  KS_p={r.ks_pvalue:.4f}  -> {r.status}")
