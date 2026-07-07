import numpy as np
from gan_fingerprint import extract_fingerprint, FingerprintResult


def test_extract_fingerprint_returns_8_features():
    img = np.random.default_rng(0).integers(0, 255, (64, 64, 3), dtype=np.uint8)
    result = extract_fingerprint(img)
    assert isinstance(result, FingerprintResult)
    assert len(result.features) == 8
    assert len(result.feature_names) == 8


def test_fingerprint_as_dict_keys_match_names():
    img = np.random.default_rng(1).integers(0, 255, (64, 64, 3), dtype=np.uint8)
    result = extract_fingerprint(img)
    d = result.as_dict()
    assert set(d.keys()) == set(result.feature_names)


def test_synthetic_samples_have_higher_mean_color_channel_correlation_than_real():
    # Compare MEAN scores over many samples rather than a single pair: the
    # injected artifacts are statistical (not guaranteed on every draw), which
    # is exactly why artifact-detection/classifier/synthetic_classifier.py
    # trains a classifier over all 8 features jointly rather than thresholding
    # a single one. color_channel_corr is the single most reliably separated
    # feature for this generator (see artifact-detection/README.md) because
    # the injected checkerboard/periodic patterns are shared identically
    # across R/G/B, unlike independent real sensor noise per channel.
    import os
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "datasets", "generators"))
    from synthetic_data_generator import make_real_sample, make_synthetic_sample

    rng = np.random.default_rng(42)
    real_scores = [extract_fingerprint(make_real_sample(rng)).as_dict()["color_channel_corr"] for _ in range(20)]
    synth_scores = [extract_fingerprint(make_synthetic_sample(rng)).as_dict()["color_channel_corr"] for _ in range(20)]

    assert np.mean(synth_scores) > np.mean(real_scores)
