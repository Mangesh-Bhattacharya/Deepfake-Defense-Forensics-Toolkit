import numpy as np
from spectrogram_artifact_detector import (
    extract_audio_fingerprint, make_real_speech_like, make_synthetic_speech_like, stft,
)


def test_stft_shape():
    signal = np.random.default_rng(0).normal(0, 1, 4000).astype(np.float32)
    spec = stft(signal, n_fft=512, hop=128)
    assert spec.shape[1] == 512 // 2 + 1
    assert spec.shape[0] > 0


def test_audio_fingerprint_has_5_features():
    rng = np.random.default_rng(0)
    sig = make_real_speech_like(rng)
    fp = extract_audio_fingerprint(sig)
    assert len(fp.features) == 5
    assert len(fp.feature_names) == 5


def test_real_and_synthetic_speech_differ_in_high_freq_energy():
    rng = np.random.default_rng(0)
    real = make_real_speech_like(rng)
    synth = make_synthetic_speech_like(rng)
    real_fp = extract_audio_fingerprint(real).as_dict()
    synth_fp = extract_audio_fingerprint(synth).as_dict()
    assert real_fp["high_freq_energy_ratio"] != synth_fp["high_freq_energy_ratio"]
