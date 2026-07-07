"""
model_robustness_evaluator.py
---------------------------------
Model robustness evaluator for the synthetic-media classifier.

Applies a battery of realistic perturbations to test images (JPEG-like
quantization, Gaussian noise, resize/upscale, brightness shift) and measures
how much classifier accuracy degrades — the standard "corruption robustness"
methodology from Hendrycks & Dietterich, 2019, "Benchmarking Neural Network
Robustness to Common Corruptions and Perturbations", adapted to this repo's
CPU-only synthetic-media classifier.

A robust deepfake detector should keep working after the image has been
re-compressed/re-uploaded through a social platform — this harness quantifies
exactly how much accuracy is lost under each corruption type.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Callable, Dict, List

import numpy as np
import cv2

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "artifact-detection", "classifier"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "artifact-detection", "image"))
from synthetic_classifier import load_dataset, SyntheticMediaClassifier  # noqa: E402


def corrupt_jpeg(img: np.ndarray, quality: int = 30) -> np.ndarray:
    ok, enc = cv2.imencode(".jpg", cv2.cvtColor(img, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, quality])
    dec = cv2.imdecode(enc, cv2.IMREAD_COLOR)
    return cv2.cvtColor(dec, cv2.COLOR_BGR2RGB)


def corrupt_gaussian_noise(img: np.ndarray, sigma: float = 15.0, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    noise = rng.normal(0, sigma, img.shape)
    return np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)


def corrupt_resize_roundtrip(img: np.ndarray, scale: float = 0.5) -> np.ndarray:
    h, w = img.shape[:2]
    small = cv2.resize(img, (max(1, int(w * scale)), max(1, int(h * scale))))
    return cv2.resize(small, (w, h))


def corrupt_brightness(img: np.ndarray, delta: int = 40) -> np.ndarray:
    return np.clip(img.astype(np.int32) + delta, 0, 255).astype(np.uint8)


CORRUPTIONS: Dict[str, Callable[[np.ndarray], np.ndarray]] = {
    "jpeg_q30": lambda im: corrupt_jpeg(im, 30),
    "gaussian_noise_sigma15": lambda im: corrupt_gaussian_noise(im, 15.0),
    "resize_roundtrip_0.5x": lambda im: corrupt_resize_roundtrip(im, 0.5),
    "brightness_+40": lambda im: corrupt_brightness(im, 40),
}


@dataclass
class RobustnessResult:
    corruption: str
    clean_accuracy: float
    corrupted_accuracy: float
    accuracy_drop: float


def evaluate_robustness(data_dir: str, model_path: str) -> List[RobustnessResult]:
    images, labels = load_dataset(data_dir)
    clf = SyntheticMediaClassifier.load(model_path)

    def accuracy(imgs):
        preds = [clf.predict_image(im)[0] for im in imgs]
        return float(np.mean(np.array(preds) == np.array(labels)))

    clean_acc = accuracy(images)
    results = []
    for name, fn in CORRUPTIONS.items():
        corrupted_imgs = [fn(im) for im in images]
        corrupted_acc = accuracy(corrupted_imgs)
        results.append(RobustnessResult(name, clean_acc, corrupted_acc, clean_acc - corrupted_acc))
    return results


if __name__ == "__main__":
    data_dir = os.path.join(os.path.dirname(__file__), "..", "datasets", "synthetic_media")
    model_path = os.path.join(os.path.dirname(__file__), "..", "models", "synthetic_classifier.pkl")
    if not os.path.exists(model_path):
        print("Train the classifier first: python3 artifact-detection/classifier/synthetic_classifier.py")
    else:
        for r in evaluate_robustness(data_dir, model_path):
            print(f"{r.corruption:26s} clean={r.clean_accuracy:.3f}  corrupted={r.corrupted_accuracy:.3f}  drop={r.accuracy_drop:+.3f}")
