"""
voice_adversarial_generator.py
---------------------------------
Voice-recognition adversarial input generator.

Generates perturbed waveforms designed to stress-test speaker-verification /
voice-recognition systems, analogous in spirit to the face attacks in
face_spoof_tests.py but for audio:

  1. pitch_shift_attack     - shifts fundamental frequency to impersonate a different speaker profile
  2. replay_attack          - simulates a low-fidelity speaker replay (band-limiting + echo)
  3. splice_attack          - concatenates two different "utterances" to synthesize new content
  4. adversarial_noise      - adds a small perceptually-quiet but structured perturbation

Each function accepts a 1-D float32 waveform in [-1, 1] and returns a
perturbed waveform of the same shape. A lightweight MFCC-like embedding
(`simple_voice_embedding`) is provided so attacks can be scored end-to-end
without any external speaker-ID model, consistent with this repo's
CPU-only / no-external-data policy.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List

import numpy as np


def simple_voice_embedding(signal: np.ndarray, sr: int = 16000, n_bands: int = 20) -> np.ndarray:
    """A dependency-free stand-in for an MFCC/d-vector speaker embedding:
    log-energy in `n_bands` mel-ish (linear here, for simplicity) frequency bands."""
    spec = np.abs(np.fft.rfft(signal * np.hanning(len(signal))))
    bands = np.array_split(spec, n_bands)
    return np.log(np.array([b.sum() for b in bands]) + 1e-6)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-8
    return float(np.dot(a, b) / denom)


def pitch_shift_attack(signal: np.ndarray, sr: int = 16000, semitones: float = 4.0) -> np.ndarray:
    factor = 2 ** (semitones / 12)
    indices = np.round(np.arange(0, len(signal), factor)).astype(int)
    indices = indices[indices < len(signal)]
    shifted = signal[indices]
    # resample back to original length (simple linear interpolation)
    x_old = np.linspace(0, 1, len(shifted))
    x_new = np.linspace(0, 1, len(signal))
    return np.interp(x_new, x_old, shifted).astype(np.float32)


def replay_attack(signal: np.ndarray, sr: int = 16000) -> np.ndarray:
    # band-limit (crude low-pass via moving average) + echo, simulating speaker playback + mic re-capture
    kernel = np.ones(9) / 9
    band_limited = np.convolve(signal, kernel, mode="same")
    delay = int(0.02 * sr)
    echo = np.zeros_like(band_limited)
    echo[delay:] = band_limited[:-delay] * 0.3
    return np.clip(band_limited + echo, -1, 1).astype(np.float32)


def splice_attack(signal_a: np.ndarray, signal_b: np.ndarray, split: float = 0.5) -> np.ndarray:
    cut = int(len(signal_a) * split)
    spliced = np.concatenate([signal_a[:cut], signal_b[cut:]])
    # smooth the seam
    w = 64
    if cut > w and len(spliced) > cut + w:
        fade = np.linspace(0, 1, 2 * w)
        seam = spliced[cut - w:cut + w]
        blended = seam * fade if len(seam) == len(fade) else seam
        spliced[cut - w:cut + w] = blended
    return spliced.astype(np.float32)


def adversarial_noise(signal: np.ndarray, epsilon: float = 0.02, seed: int = 3) -> np.ndarray:
    rng = np.random.default_rng(seed)
    # structured (banded) perturbation rather than pure white noise, mimicking
    # a gradient-crafted perturbation that concentrates energy in perceptually-masked bands
    t = np.arange(len(signal))
    structured = epsilon * np.sin(2 * np.pi * 0.15 * t) * rng.choice([-1, 1], size=len(signal))
    return np.clip(signal + structured, -1, 1).astype(np.float32)


@dataclass
class VoiceAttackResult:
    attack_name: str
    similarity_to_enrolled: float
    match_threshold: float
    fooled_system: bool


def run_voice_attack_battery(
    enrolled: np.ndarray, probe: np.ndarray, sr: int = 16000, match_threshold: float = 0.9
) -> List[VoiceAttackResult]:
    enrolled_emb = simple_voice_embedding(enrolled, sr)
    attacks: Dict[str, Callable[[np.ndarray], np.ndarray]] = {
        "pitch_shift_attack": lambda s: pitch_shift_attack(s, sr),
        "replay_attack": lambda s: replay_attack(s, sr),
        "adversarial_noise": lambda s: adversarial_noise(s),
    }
    results = []
    for name, fn in attacks.items():
        perturbed = fn(probe)
        emb = simple_voice_embedding(perturbed, sr)
        sim = cosine_similarity(enrolled_emb, emb)
        results.append(VoiceAttackResult(name, sim, match_threshold, sim >= match_threshold))
    return results


if __name__ == "__main__":
    import os
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "artifact-detection", "audio"))
    from spectrogram_artifact_detector import make_real_speech_like  # noqa: E402

    rng = np.random.default_rng(0)
    enrolled = make_real_speech_like(rng)
    probe = make_real_speech_like(rng)
    for r in run_voice_attack_battery(enrolled, probe):
        status = "FOOLED SYSTEM" if r.fooled_system else "blocked"
        print(f"{r.attack_name:20s} sim={r.similarity_to_enrolled:.3f}  threshold={r.match_threshold}  -> {status}")
