import numpy as np
from guardrail_scoring import sweep_thresholds, recommend_threshold


def test_sweep_thresholds_returns_metrics_for_every_step():
    y_true = [0, 0, 1, 1]
    y_scores = [0.1, 0.4, 0.6, 0.9]
    results = sweep_thresholds(y_true, y_scores, n_steps=11)
    assert len(results) == 11
    for m in results:
        assert 0.0 <= m.precision <= 1.0
        assert 0.0 <= m.recall <= 1.0


def test_recommend_threshold_max_f1_perfect_separation():
    y_true = [0] * 20 + [1] * 20
    rng = np.random.default_rng(0)
    y_scores = np.concatenate([rng.uniform(0, 0.3, 20), rng.uniform(0.7, 1.0, 20)])
    metrics = sweep_thresholds(y_true, y_scores)
    best = recommend_threshold(metrics, policy="max_f1")
    assert best.f1 > 0.9


def test_recommend_threshold_safety_policy_respects_fpr_when_possible():
    y_true = [0] * 20 + [1] * 20
    rng = np.random.default_rng(0)
    y_scores = np.concatenate([rng.uniform(0, 0.3, 20), rng.uniform(0.7, 1.0, 20)])
    metrics = sweep_thresholds(y_true, y_scores)
    best = recommend_threshold(metrics, policy="min_fnr_subject_to_fpr", max_fpr=0.05)
    min_fpr = min(m.false_positive_rate for m in metrics)
    assert best.false_positive_rate <= 0.05 + 1e-9 or best.false_positive_rate == min_fpr
