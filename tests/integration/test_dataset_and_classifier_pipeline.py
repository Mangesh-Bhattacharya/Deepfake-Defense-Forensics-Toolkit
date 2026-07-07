"""Integration test: dataset generation -> classifier training -> evaluation,
exercised end-to-end exactly like a fresh checkout would run it."""
import os
import tempfile

from synthetic_data_generator import generate_dataset
from synthetic_classifier import train_and_evaluate


def test_generate_train_evaluate_pipeline():
    with tempfile.TemporaryDirectory() as d:
        data_dir = os.path.join(d, "synthetic_media")
        manifest_path = generate_dataset(data_dir, n_per_class=20, seed=1)
        assert os.path.exists(manifest_path)

        report = train_and_evaluate(data_dir, model_name="logreg", test_size=0.3, seed=1)
        assert report.n_train + report.n_test == 40
        assert 0.0 <= report.accuracy <= 1.0
        assert 0.0 <= report.roc_auc <= 1.0
        # the injected artifacts are overt-by-design (see artifact-detection/README.md),
        # so a sane classifier should comfortably beat random guessing
        assert report.accuracy > 0.6
