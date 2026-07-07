"""
annotation_workflow_simulator.py
------------------------------------
Simulates the annotation/evaluation workflow used by AI-community-style data
labeling pipelines (task assignment -> multi-annotator labeling -> agreement
scoring -> adjudication of disagreements), applied to the synthetic-media
dataset produced by datasets/generators/synthetic_data_generator.py.

Computes Cohen's Kappa (2 annotators) and Fleiss' Kappa (3+ annotators) —
the standard inter-annotator agreement metrics used to gate annotator
qualification and monitor labeling quality over time.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict, List

import numpy as np


@dataclass
class AnnotationTask:
    task_id: str
    filename: str
    ground_truth: str  # only used for simulation/QA, hidden from "annotators"


@dataclass
class AnnotatorLabel:
    annotator_id: str
    task_id: str
    label: str
    confidence: float


def cohens_kappa(labels_a: List[str], labels_b: List[str]) -> float:
    assert len(labels_a) == len(labels_b)
    categories = sorted(set(labels_a) | set(labels_b))
    idx = {c: i for i, c in enumerate(categories)}
    n = len(labels_a)
    cm = np.zeros((len(categories), len(categories)))
    for a, b in zip(labels_a, labels_b):
        cm[idx[a], idx[b]] += 1
    po = np.trace(cm) / n
    row_marg = cm.sum(axis=1) / n
    col_marg = cm.sum(axis=0) / n
    pe = float(np.sum(row_marg * col_marg))
    if pe == 1.0:
        return 1.0
    return float((po - pe) / (1 - pe))


def fleiss_kappa(annotations: Dict[str, List[str]]) -> float:
    """annotations: {task_id: [label_from_annotator_1, label_from_annotator_2, ...]}"""
    categories = sorted({label for labels in annotations.values() for label in labels})
    n_items = len(annotations)
    n_raters = len(next(iter(annotations.values())))

    matrix = np.zeros((n_items, len(categories)))
    for i, (task_id, labels) in enumerate(annotations.items()):
        for label in labels:
            matrix[i, categories.index(label)] += 1

    p_i = (np.sum(matrix ** 2, axis=1) - n_raters) / (n_raters * (n_raters - 1))
    P_bar = float(np.mean(p_i))

    p_j = matrix.sum(axis=0) / (n_items * n_raters)
    P_e = float(np.sum(p_j ** 2))

    if P_e == 1.0:
        return 1.0
    return (P_bar - P_e) / (1 - P_e)


def simulate_annotators(
    manifest: List[dict], n_annotators: int = 3, noise_rate: float = 0.1, seed: int = 0
) -> Dict[str, List[str]]:
    """Simulates N annotators labeling every task, each with an independent
    chance (`noise_rate`) of mislabeling relative to ground truth — modeling
    realistic human labeling noise."""
    rng = np.random.default_rng(seed)
    annotations: Dict[str, List[str]] = {}
    for rec in manifest:
        task_id = rec["filename"]
        truth = rec["label"]
        labels = []
        for a in range(n_annotators):
            if rng.random() < noise_rate:
                labels.append("real" if truth == "synthetic" else "synthetic")
            else:
                labels.append(truth)
        annotations[task_id] = labels
    return annotations


def majority_vote_adjudication(annotations: Dict[str, List[str]]) -> Dict[str, str]:
    from collections import Counter
    return {task_id: Counter(labels).most_common(1)[0][0] for task_id, labels in annotations.items()}


def run_simulation(manifest_path: str, n_annotators: int = 3, noise_rate: float = 0.15, seed: int = 0) -> dict:
    with open(manifest_path) as f:
        manifest = json.load(f)

    annotations = simulate_annotators(manifest, n_annotators, noise_rate, seed)
    adjudicated = majority_vote_adjudication(annotations)

    truth_map = {rec["filename"]: rec["label"] for rec in manifest}
    adjudicated_accuracy = float(np.mean([
        adjudicated[tid] == truth_map[tid] for tid in adjudicated
    ]))

    kappa = fleiss_kappa(annotations)

    return {
        "n_tasks": len(manifest),
        "n_annotators": n_annotators,
        "noise_rate": noise_rate,
        "fleiss_kappa": round(kappa, 4),
        "adjudicated_accuracy": round(adjudicated_accuracy, 4),
        "kappa_interpretation": interpret_kappa(kappa),
    }


def interpret_kappa(kappa: float) -> str:
    # Landis & Koch (1977) benchmark scale
    if kappa < 0:
        return "poor (worse than chance)"
    if kappa < 0.20:
        return "slight agreement"
    if kappa < 0.40:
        return "fair agreement"
    if kappa < 0.60:
        return "moderate agreement"
    if kappa < 0.80:
        return "substantial agreement"
    return "almost perfect agreement"


if __name__ == "__main__":
    manifest_path = os.path.join(os.path.dirname(__file__), "..", "datasets", "synthetic_media", "manifest.json")
    if not os.path.exists(manifest_path):
        print("Generate the dataset first: python3 datasets/generators/synthetic_data_generator.py")
    else:
        result = run_simulation(manifest_path)
        print(json.dumps(result, indent=2))
