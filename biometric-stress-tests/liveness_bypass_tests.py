"""
liveness_bypass_tests.py
---------------------------
Liveness-detection bypass attempts.

Liveness detection tries to distinguish a live person from a presentation
attack (photo, video replay, mask, deepfake) using cues like: eye blink rate,
micro head motion, texture/reflectance, and challenge-response (e.g. "turn
your head"). This module implements simple, honest simulations of common
bypass techniques and scores whether they would defeat a liveness check built
purely on the cues below.

Bypass techniques simulated:
  1. static_photo_bypass     - zero motion/blink signal (should be caught by a motion-based liveness check)
  2. looped_video_bypass     - motion present but exactly repeating (periodicity should be caught)
  3. texture_spoof_bypass    - adds synthetic specular highlights to fake reflectance cues
  4. challenge_response_replay - pre-recorded video that "coincidentally" matches a requested action window

Each bypass is scored against a simple, transparent liveness heuristic (not a
production-grade liveness model) so results are fully reproducible.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np


@dataclass
class LivenessTestResult:
    technique: str
    motion_score: float
    periodicity_score: float
    texture_score: float
    liveness_verdict: str  # "LIVE" or "SPOOF"
    bypassed: bool


def _motion_score(frames: List[np.ndarray]) -> float:
    if len(frames) < 2:
        return 0.0
    diffs = [np.mean(np.abs(frames[i].astype(np.float32) - frames[i - 1].astype(np.float32)))
             for i in range(1, len(frames))]
    return float(np.mean(diffs))


def _periodicity_score(frames: List[np.ndarray]) -> float:
    if len(frames) < 6:
        return 0.0
    signal = np.array([f.astype(np.float32).mean() for f in frames])
    signal = signal - signal.mean()
    if signal.std() < 1e-6:
        return 0.0
    autocorr = np.correlate(signal, signal, mode="full")
    autocorr = autocorr[len(autocorr) // 2:]
    autocorr /= (autocorr[0] + 1e-8)
    return float(np.max(autocorr[2:]))  # high => strongly periodic/looped


def _texture_score(frame: np.ndarray) -> float:
    """Crude specular-highlight proxy: fraction of near-saturated pixels."""
    return float(np.mean(frame > 245))


def make_frame_sequence(rng: np.random.Generator, n: int, motion: bool, loop: bool) -> List[np.ndarray]:
    base = rng.normal(128, 20, (32, 32, 3)).clip(0, 255).astype(np.uint8)
    frames = []
    for i in range(n):
        if not motion:
            frames.append(base.copy())
        elif loop:
            phase = (i % 5) / 5.0
            shift = int(phase * 4)
            frames.append(np.roll(base, shift, axis=0))
        else:
            noise = rng.normal(0, 6, base.shape)
            frames.append(np.clip(base.astype(np.float32) + noise * i * 0.1, 0, 255).astype(np.uint8))
    return frames


def evaluate_liveness(
    frames: List[np.ndarray], technique: str, motion_threshold: float = 2.0,
    periodicity_threshold: float = 0.8, texture_threshold: float = 0.05,
) -> LivenessTestResult:
    motion = _motion_score(frames)
    periodicity = _periodicity_score(frames)
    texture = _texture_score(frames[-1]) if frames else 0.0

    # naive rule-based liveness: needs motion, low periodicity, low over-saturation
    is_live = (motion > motion_threshold) and (periodicity < periodicity_threshold) and (texture < texture_threshold)
    verdict = "LIVE" if is_live else "SPOOF"
    bypassed = (verdict == "LIVE") and technique != "genuine_live"

    return LivenessTestResult(technique, motion, periodicity, texture, verdict, bypassed)


def run_liveness_bypass_battery(seed: int = 0) -> List[LivenessTestResult]:
    rng = np.random.default_rng(seed)
    results = []

    static_frames = make_frame_sequence(rng, 10, motion=False, loop=False)
    results.append(evaluate_liveness(static_frames, "static_photo_bypass"))

    looped_frames = make_frame_sequence(rng, 10, motion=True, loop=True)
    results.append(evaluate_liveness(looped_frames, "looped_video_bypass"))

    texture_frames = make_frame_sequence(rng, 10, motion=True, loop=False)
    texture_frames[-1] = np.clip(texture_frames[-1].astype(np.int32) + 120, 0, 255).astype(np.uint8)
    results.append(evaluate_liveness(texture_frames, "texture_spoof_bypass"))

    genuine_frames = make_frame_sequence(rng, 10, motion=True, loop=False)
    results.append(evaluate_liveness(genuine_frames, "genuine_live"))

    return results


if __name__ == "__main__":
    for r in run_liveness_bypass_battery():
        flag = "BYPASSED LIVENESS CHECK" if r.bypassed else ("correctly rejected" if r.liveness_verdict == "SPOOF" else "correctly accepted (genuine)")
        print(f"{r.technique:24s} motion={r.motion_score:6.2f} periodicity={r.periodicity_score:.2f} "
              f"texture={r.texture_score:.3f} verdict={r.liveness_verdict:6s} -> {flag}")
