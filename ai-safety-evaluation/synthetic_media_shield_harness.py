"""
synthetic_media_shield_harness.py
-------------------------------------
Synthetic media "shield" testing harness.

Simulates a content-safety gate (e.g. an upload pipeline that must decide
ALLOW / REVIEW / BLOCK for incoming media) sitting on top of the classifier
from artifact-detection/. Tests the shield's end-to-end behavior against:
  1. clean real & synthetic media (expected baseline behavior)
  2. adversarially perturbed synthetic media (attempts to sneak a deepfake past
     the shield by adding noise/blur to reduce the classifier's confidence)

Reports how many adversarial "bypass attempts" succeed at each shield
threshold configuration, similar in spirit to biometric-stress-tests but for
the content-moderation shield itself.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import List

import numpy as np
import cv2

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "artifact-detection", "classifier"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "artifact-detection", "image"))
from synthetic_classifier import load_dataset, SyntheticMediaClassifier  # noqa: E402


@dataclass
class ShieldDecision:
    filename_index: int
    true_label: str
    classifier_score: float
    decision: str  # ALLOW / REVIEW / BLOCK


@dataclass
class ShieldEvalReport:
    review_threshold: float
    block_threshold: float
    decisions: List[ShieldDecision]
    bypass_count: int
    bypass_rate: float


def shield_decide(score: float, review_threshold: float, block_threshold: float) -> str:
    if score >= block_threshold:
        return "BLOCK"
    if score >= review_threshold:
        return "REVIEW"
    return "ALLOW"


def evasion_perturbation(img: np.ndarray, strength: float = 8.0, seed: int = 5) -> np.ndarray:
    """A mild blur + low-amplitude noise intended to wash out the GAN fingerprint
    signal the classifier relies on, simulating an adversary trying to sneak
    synthetic media past the shield."""
    blurred = cv2.GaussianBlur(img, (3, 3), 0).astype(np.float32)
    rng = np.random.default_rng(seed)
    noise = rng.normal(0, strength, img.shape)
    return np.clip(blurred + noise, 0, 255).astype(np.uint8)


def run_shield_evaluation(
    data_dir: str, model_path: str, review_threshold: float = 0.4,
    block_threshold: float = 0.7, adversarial: bool = False,
) -> ShieldEvalReport:
    images, labels = load_dataset(data_dir)
    clf = SyntheticMediaClassifier.load(model_path)

    decisions = []
    bypasses = 0
    for i, (img, label) in enumerate(zip(images, labels)):
        test_img = evasion_perturbation(img) if (adversarial and label == 1) else img
        _, score = clf.predict_image(test_img)
        decision = shield_decide(score, review_threshold, block_threshold)
        decisions.append(ShieldDecision(i, "synthetic" if label == 1 else "real", round(score, 4), decision))
        if label == 1 and decision == "ALLOW":
            bypasses += 1

    n_synthetic = sum(1 for lbl in labels if lbl == 1)
    bypass_rate = bypasses / n_synthetic if n_synthetic else 0.0
    return ShieldEvalReport(review_threshold, block_threshold, decisions, bypasses, bypass_rate)


if __name__ == "__main__":
    data_dir = os.path.join(os.path.dirname(__file__), "..", "datasets", "synthetic_media")
    model_path = os.path.join(os.path.dirname(__file__), "..", "models", "synthetic_classifier.pkl")
    if not os.path.exists(model_path):
        print("Train the classifier first: python3 artifact-detection/classifier/synthetic_classifier.py")
    else:
        baseline = run_shield_evaluation(data_dir, model_path, adversarial=False)
        attacked = run_shield_evaluation(data_dir, model_path, adversarial=True)
        print(f"Baseline (no evasion attempt):  bypasses={baseline.bypass_count}  bypass_rate={baseline.bypass_rate:.1%}")
        print(f"Under evasion perturbation:      bypasses={attacked.bypass_count}  bypass_rate={attacked.bypass_rate:.1%}")
