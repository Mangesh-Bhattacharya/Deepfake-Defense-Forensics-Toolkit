import numpy as np
from face_spoof_tests import cosine_similarity, run_spoof_battery
from liveness_bypass_tests import run_liveness_bypass_battery


def test_cosine_similarity_identical_vectors_is_one():
    v = np.array([1.0, 2.0, 3.0])
    assert abs(cosine_similarity(v, v) - 1.0) < 1e-9


def test_spoof_battery_returns_all_attack_types():
    rng = np.random.default_rng(0)
    img = rng.integers(0, 255, (64, 64, 3), dtype=np.uint8)
    results = run_spoof_battery(img, img)
    names = {r.attack_name for r in results}
    assert names == {"print_attack", "replay_attack", "mask_attack", "adversarial_patch"}


def test_liveness_battery_flags_static_photo_as_spoof():
    results = run_liveness_bypass_battery(seed=1)
    static = next(r for r in results if r.technique == "static_photo_bypass")
    assert static.liveness_verdict == "SPOOF"


def test_genuine_live_sequence_accepted():
    results = run_liveness_bypass_battery(seed=1)
    genuine = next(r for r in results if r.technique == "genuine_live")
    assert genuine.liveness_verdict == "LIVE"
