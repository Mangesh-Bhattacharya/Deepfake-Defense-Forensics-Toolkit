"""
synthetic_classifier.py
-------------------------
Synthetic-artifact classifier.

HONEST SCOPE NOTE (read this first)
The job posting references CNN/ViT-based deepfake classifiers. Training a real
CNN/ViT requires a GPU, thousands-to-millions of labeled real deepfake frames,
and hours of compute — none of which exist in this repo's execution
environment. Rather than fake that with a hard-coded "97% accuracy" number,
this module trains a small, genuinely-working **Gradient Boosted / Logistic
Regression classifier** (scikit-learn, CPU, seconds to train) on the 8-dim GAN
fingerprint features from `gan_fingerprint.py`, evaluated on the locally
generated synthetic dataset. It is architected so the feature extractor can be
swapped for a real CNN/ViT backbone (e.g. a frozen timm ViT + linear probe)
without changing any downstream code — see `SyntheticMediaClassifier.predict()`
and the `# SWAP-IN POINT` comment below.

This keeps every claim in this repo verifiable: you can run
`python3 synthetic_classifier.py` right now and see real train/test accuracy,
a real confusion matrix, and a real ROC-AUC on held-out synthetic data.
"""
from __future__ import annotations

import json
import os
import pickle
import sys
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np
import cv2
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score, confusion_matrix, classification_report

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "image"))
from gan_fingerprint import extract_fingerprint  # noqa: E402

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "models", "synthetic_classifier.pkl")


@dataclass
class TrainReport:
    accuracy: float
    roc_auc: float
    confusion_matrix: List[List[int]]
    classification_report: str
    n_train: int
    n_test: int


class SyntheticMediaClassifier:
    """Wraps a fitted sklearn classifier over GAN-fingerprint features.

    SWAP-IN POINT: to use a real CNN/ViT backbone instead of hand-crafted
    fingerprint features, replace `self._featurize` with a call to a frozen
    torch/timm feature extractor (e.g. `vit_base_patch16_224`), keep the same
    (N, D) numpy feature matrix contract, and everything downstream — training,
    scoring, reporting — keeps working unmodified.
    """

    def __init__(self, model=None):
        self.model = model or LogisticRegression(max_iter=1000)

    def _featurize(self, img: np.ndarray) -> np.ndarray:
        return np.array(extract_fingerprint(img).features)

    def fit(self, images: List[np.ndarray], labels: List[int]) -> None:
        X = np.stack([self._featurize(im) for im in images])
        y = np.array(labels)
        self.model.fit(X, y)

    def score(self, feature_vector: np.ndarray) -> float:
        """Return P(synthetic) in [0, 1] for a single precomputed feature vector."""
        proba = self.model.predict_proba(feature_vector.reshape(1, -1))[0]
        classes = list(self.model.classes_)
        return float(proba[classes.index(1)]) if 1 in classes else float(proba[-1])

    def predict_image(self, img: np.ndarray) -> Tuple[int, float]:
        fv = self._featurize(img)
        pred = int(self.model.predict(fv.reshape(1, -1))[0])
        return pred, self.score(fv)

    def save(self, path: str = MODEL_PATH) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self.model, f)

    @classmethod
    def load(cls, path: str = MODEL_PATH) -> "SyntheticMediaClassifier":
        with open(path, "rb") as f:
            # nosec B301 -- this loads a .pkl this same toolkit trains and writes
            # locally (see save() above); never point MODEL_PATH at an untrusted file.
            model = pickle.load(f)  # nosec B301
        return cls(model=model)


def load_dataset(data_dir: str) -> Tuple[List[np.ndarray], List[int]]:
    manifest_path = os.path.join(data_dir, "manifest.json")
    with open(manifest_path) as f:
        manifest = json.load(f)
    images, labels = [], []
    for rec in manifest:
        img = cv2.cvtColor(cv2.imread(os.path.join(data_dir, rec["filename"])), cv2.COLOR_BGR2RGB)
        images.append(img)
        labels.append(1 if rec["label"] == "synthetic" else 0)
    return images, labels


def train_and_evaluate(data_dir: str, model_name: str = "logreg", test_size: float = 0.25, seed: int = 42) -> TrainReport:
    images, labels = load_dataset(data_dir)
    X = np.stack([extract_fingerprint(im).features for im in images])
    y = np.array(labels)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=seed, stratify=y
    )

    model = GradientBoostingClassifier(random_state=seed) if model_name == "gboost" else LogisticRegression(max_iter=1000)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    report = TrainReport(
        accuracy=float(accuracy_score(y_test, y_pred)),
        roc_auc=float(roc_auc_score(y_test, y_proba)),
        confusion_matrix=confusion_matrix(y_test, y_pred).tolist(),
        classification_report=classification_report(y_test, y_pred, target_names=["real", "synthetic"]),
        n_train=len(y_train),
        n_test=len(y_test),
    )

    clf = SyntheticMediaClassifier(model=model)
    clf.save()
    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default=os.path.join(os.path.dirname(__file__), "..", "..", "datasets", "synthetic_media"))
    parser.add_argument("--model", choices=["logreg", "gboost"], default="logreg")
    args = parser.parse_args()

    report = train_and_evaluate(args.data_dir, model_name=args.model)
    print(f"Train samples: {report.n_train}  Test samples: {report.n_test}")
    print(f"Accuracy: {report.accuracy:.4f}   ROC-AUC: {report.roc_auc:.4f}")
    print("Confusion matrix [[TN,FP],[FN,TP]]:", report.confusion_matrix)
    print(report.classification_report)
