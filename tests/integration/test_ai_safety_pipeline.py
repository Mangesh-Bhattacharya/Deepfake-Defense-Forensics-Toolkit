"""Integration test: train classifier -> robustness eval -> shield harness ->
drift detection, using a fresh temp dataset/model so this test doesn't depend
on artifacts left over from other test runs."""
import os
import tempfile

from synthetic_data_generator import generate_dataset
from synthetic_classifier import train_and_evaluate
from model_robustness_evaluator import evaluate_robustness
from synthetic_media_shield_harness import run_shield_evaluation


def test_ai_safety_tools_run_end_to_end():
    with tempfile.TemporaryDirectory() as d:
        data_dir = os.path.join(d, "synthetic_media")
        generate_dataset(data_dir, n_per_class=15, seed=3)
        model_path = os.path.join(d, "model.pkl")

        train_and_evaluate(data_dir, model_name="logreg", seed=3)
        # train_and_evaluate saves to the default MODEL_PATH; also save a copy locally
        import shutil
        from synthetic_classifier import MODEL_PATH
        shutil.copy(MODEL_PATH, model_path)

        robustness_results = evaluate_robustness(data_dir, model_path)
        assert len(robustness_results) == 4
        for r in robustness_results:
            assert 0.0 <= r.clean_accuracy <= 1.0
            assert 0.0 <= r.corrupted_accuracy <= 1.0

        shield_report = run_shield_evaluation(data_dir, model_path, adversarial=True)
        assert 0.0 <= shield_report.bypass_rate <= 1.0
