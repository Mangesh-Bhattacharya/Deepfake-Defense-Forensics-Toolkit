"""
gan_fingerprint.py
-------------------
Pixel-level GAN "fingerprint" extractor.

GAN and diffusion upsampling layers (transposed conv / nearest-neighbour +
conv, pixel-shuffle, etc.) leave a periodic signature in the 2D frequency
spectrum of generated images that real camera-captured images do not have
(Zhang et al. 2019; Frank et al. 2020; Durall et al. 2020 "Watch your
Up-Convolution"). This module extracts that fingerprint as a fixed-length
feature vector suitable for a classifier.

Feature vector (8 dims):
  0. high_freq_energy_ratio  - energy in outer spectral ring / total energy
  1. spectral_peak_count     - number of statistically significant frequency peaks
  2. spectral_peak_max_z     - z-score of the strongest peak
  3. checkerboard_score      - correlation with a canonical checkerboard kernel
  4. local_variance_std      - std-dev of block-wise local variance (over-smoothing cue)
  5. edge_sharpness_kurtosis - kurtosis of Laplacian response (unnaturally sharp edges)
  6. color_channel_corr      - mean abs correlation between R/G/B noise residuals
  7. noise_residual_entropy  - Shannon entropy of the high-pass noise residual
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import numpy as np
import cv2


@dataclass
class FingerprintResult:
    features: List[float]
    feature_names: List[str] = field(default_factory=lambda: [
        "high_freq_energy_ratio",
        "spectral_peak_count",
        "spectral_peak_max_z",
        "checkerboard_score",
        "local_variance_std",
        "edge_sharpness_kurtosis",
        "color_channel_corr",
        "noise_residual_entropy",
    ])

    def as_dict(self) -> dict:
        return dict(zip(self.feature_names, self.features))


def _to_gray(img: np.ndarray) -> np.ndarray:
    if img.ndim == 3:
        return cv2.cvtColor(img, cv2.COLOR_RGB2GRAY).astype(np.float32)
    return img.astype(np.float32)


def _spectral_features(gray: np.ndarray) -> tuple[float, int, float]:
    f = np.fft.fftshift(np.fft.fft2(gray))
    mag = np.abs(f)
    h, w = mag.shape
    cy, cx = h // 2, w // 2
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    max_r = r.max()

    total_energy = float((mag ** 2).sum()) + 1e-8
    outer_mask = r > (0.6 * max_r)
    high_freq_energy_ratio = float((mag[outer_mask] ** 2).sum() / total_energy)

    flat = mag.flatten()
    mu, sigma = flat.mean(), flat.std() + 1e-8
    z = (flat - mu) / sigma
    peak_count = int((z > 4.0).sum())
    peak_max_z = float(z.max())

    return high_freq_energy_ratio, peak_count, peak_max_z


def _checkerboard_score(gray: np.ndarray) -> float:
    kernel = np.array([[1, -1, 1], [-1, 1, -1], [1, -1, 1]], dtype=np.float32)
    resp = cv2.filter2D(gray, -1, kernel)
    return float(np.abs(resp).mean() / (gray.std() + 1e-8))


def _local_variance_std(gray: np.ndarray, block: int = 8) -> float:
    h, w = gray.shape
    variances = []
    for y in range(0, h - block, block):
        for x in range(0, w - block, block):
            variances.append(gray[y:y + block, x:x + block].var())
    return float(np.std(variances)) if variances else 0.0


def _edge_sharpness_kurtosis(gray: np.ndarray) -> float:
    lap = cv2.Laplacian(gray, cv2.CV_32F)
    flat = lap.flatten()
    mu, sigma = flat.mean(), flat.std() + 1e-8
    m4 = np.mean((flat - mu) ** 4)
    return float(m4 / (sigma ** 4) - 3.0)  # excess kurtosis


def _color_channel_corr(img: np.ndarray) -> float:
    if img.ndim != 3 or img.shape[2] < 3:
        return 0.0
    residuals = []
    for c in range(3):
        chan = img[:, :, c].astype(np.float32)
        blur = cv2.GaussianBlur(chan, (3, 3), 0)
        residuals.append((chan - blur).flatten())
    corrs = []
    for i in range(3):
        for j in range(i + 1, 3):
            if residuals[i].std() > 1e-6 and residuals[j].std() > 1e-6:
                corrs.append(abs(np.corrcoef(residuals[i], residuals[j])[0, 1]))
    return float(np.mean(corrs)) if corrs else 0.0


def _noise_residual_entropy(gray: np.ndarray) -> float:
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    residual = gray - blur
    hist, _ = np.histogram(residual, bins=64, density=True)
    hist = hist[hist > 0]
    return float(-np.sum(hist * np.log2(hist)) / 6.0)  # normalized-ish


def extract_fingerprint(img: np.ndarray) -> FingerprintResult:
    """Extract the 8-dim GAN fingerprint feature vector from an RGB image (uint8)."""
    gray = _to_gray(img)
    hf_ratio, peak_count, peak_max_z = _spectral_features(gray)
    features = [
        hf_ratio,
        float(peak_count),
        peak_max_z,
        _checkerboard_score(gray),
        _local_variance_std(gray),
        _edge_sharpness_kurtosis(gray),
        _color_channel_corr(img),
        _noise_residual_entropy(gray),
    ]
    return FingerprintResult(features=features)


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if path:
        img = cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2RGB)
        result = extract_fingerprint(img)
        for k, v in result.as_dict().items():
            print(f"{k:28s}: {v:.4f}")
    else:
        print("Usage: python3 gan_fingerprint.py <image_path>")
