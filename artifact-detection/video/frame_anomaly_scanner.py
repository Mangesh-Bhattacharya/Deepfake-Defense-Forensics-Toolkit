"""
frame_anomaly_scanner.py
--------------------------
Video frame-level anomaly scanner.

Deepfake video generation (face-swap, reenactment, lip-sync) is applied
frame-by-frame or in short temporal windows, which tends to break the smooth
temporal consistency of real video. This scanner extracts frames from a video
(or accepts a directory of frames / a synthetic in-memory sequence), computes
the GAN fingerprint of each frame (via artifact-detection/image/gan_fingerprint.py),
and flags:

  1. Per-frame anomaly score (via the trained classifier, see ../classifier/)
  2. Temporal jitter: large frame-to-frame jumps in fingerprint features,
     which indicate blending/warping seams typical of face-swap deepfakes.
  3. Blink / mouth-region flicker proxy: variance of a central ROI over time
     (a lightweight stand-in for eye-blink consistency checks used in real
     deepfake forensics, e.g. Li et al. 2018 "In Ictu Oculi").

This module works on any video file OpenCV can decode, OR on a directory of
PNG/JPG frames, OR on an in-memory list of numpy arrays (used by tests).
"""
from __future__ import annotations

import os
import glob
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

import numpy as np
import cv2

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "image"))
from gan_fingerprint import extract_fingerprint  # noqa: E402


@dataclass
class FrameResult:
    index: int
    fingerprint: List[float]
    temporal_jitter: float
    roi_flicker: float
    anomaly_score: float


@dataclass
class ScanReport:
    frame_results: List[FrameResult]
    mean_anomaly_score: float
    max_temporal_jitter: float
    flagged_frames: List[int] = field(default_factory=list)

    def summary(self) -> dict:
        return {
            "num_frames": len(self.frame_results),
            "mean_anomaly_score": round(self.mean_anomaly_score, 4),
            "max_temporal_jitter": round(self.max_temporal_jitter, 4),
            "flagged_frames": self.flagged_frames,
        }


def load_frames_from_video(path: str, max_frames: Optional[int] = None) -> List[np.ndarray]:
    cap = cv2.VideoCapture(path)
    frames = []
    while cap.isOpened():
        ok, frame = cap.read()
        if not ok:
            break
        frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        if max_frames and len(frames) >= max_frames:
            break
    cap.release()
    return frames


def load_frames_from_dir(path: str) -> List[np.ndarray]:
    files = sorted(glob.glob(os.path.join(path, "*.png")) + glob.glob(os.path.join(path, "*.jpg")))
    return [cv2.cvtColor(cv2.imread(f), cv2.COLOR_BGR2RGB) for f in files]


def _roi_flicker(frame: np.ndarray) -> float:
    h, w = frame.shape[:2]
    roi = frame[h // 3: 2 * h // 3, w // 3: 2 * w // 3]
    return float(np.var(cv2.cvtColor(roi, cv2.COLOR_RGB2GRAY).astype(np.float32)))


def scan_frames(frames: Sequence[np.ndarray], classifier=None, jitter_threshold: float = 3.0) -> ScanReport:
    """Scan a sequence of RGB uint8 frames for synthetic-media anomalies.

    `classifier` is optional; if provided it must implement `.score(feature_vector)
    -> float in [0,1]`. If omitted, a heuristic score based on fingerprint magnitude
    is used instead (still useful as a self-contained anomaly signal).
    """
    results: List[FrameResult] = []
    prev_fp: Optional[np.ndarray] = None
    flagged: List[int] = []

    for i, frame in enumerate(frames):
        fp = np.array(extract_fingerprint(frame).features)
        jitter = float(np.linalg.norm(fp - prev_fp)) if prev_fp is not None else 0.0
        flicker = _roi_flicker(frame)

        if classifier is not None:
            score = float(classifier.score(fp))
        else:
            # heuristic fallback: normalize a couple of the most informative dims
            score = float(np.clip(0.15 * fp[0] * 10 + 0.05 * fp[3] + 0.02 * fp[1], 0, 1))

        results.append(FrameResult(i, fp.tolist(), jitter, flicker, score))
        if jitter > jitter_threshold or score > 0.7:
            flagged.append(i)
        prev_fp = fp

    mean_score = float(np.mean([r.anomaly_score for r in results])) if results else 0.0
    max_jitter = float(np.max([r.temporal_jitter for r in results])) if results else 0.0
    return ScanReport(results, mean_score, max_jitter, flagged)


def scan_video(path: str, max_frames: int = 60, classifier=None) -> ScanReport:
    frames = load_frames_from_video(path, max_frames=max_frames)
    return scan_frames(frames, classifier=classifier)


if __name__ == "__main__":
    import argparse
    import json as _json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="video file or directory of frames")
    parser.add_argument("--max-frames", type=int, default=60)
    args = parser.parse_args()

    if os.path.isdir(args.path):
        frames = load_frames_from_dir(args.path)
    else:
        frames = load_frames_from_video(args.path, max_frames=args.max_frames)

    report = scan_frames(frames)
    print(_json.dumps(report.summary(), indent=2))
