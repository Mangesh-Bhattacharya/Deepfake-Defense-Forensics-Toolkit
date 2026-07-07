"""
synthetic_data_generator.py
----------------------------
Generates a small, fully local "real vs synthetic" image dataset for demo and
unit-test purposes.

SCOPE NOTE
This toolkit does not ship or download any real deepfake corpus (no
FaceForensics++, no DFDC, no scraped faces). It procedurally generates toy
"real" and "synthetic" samples with statistically distinguishable properties,
so every detector in this repo can be trained/evaluated end-to-end without
external data, without a GPU, and without privacy/licensing concerns.

"Real" samples: smooth natural-image-like gradients + organic sensor noise.

"Synthetic" samples: images built with GAN/diffusion-style artifacts injected
on purpose: checkerboard upsampling patterns, periodic frequency-domain
components, and over-smoothed local patches. These mirror well-documented
detection cues (Zhang et al. 2019 "Detecting and Simulating Artifacts in GAN
Fake Images"; Frank et al. 2020 "Leveraging Frequency Analysis for Deep Fake
Image Recognition").

Usage:
    python3 synthetic_data_generator.py --out ../synthetic_media --n 150
"""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass, asdict

import numpy as np
import cv2

IMG_SIZE = 64


@dataclass
class SampleRecord:
    filename: str
    label: str
    seed: int
    generator: str


def _gaussian_blur(img: np.ndarray, k: int = 5) -> np.ndarray:
    return cv2.GaussianBlur(img, (k, k), 0)


def make_real_sample(rng: np.random.Generator) -> np.ndarray:
    base = rng.normal(loc=128, scale=25, size=(IMG_SIZE, IMG_SIZE, 3)).astype(np.float32)
    blurred = _gaussian_blur(np.clip(base, 0, 255).astype(np.uint8), k=7).astype(np.float32)
    noise = rng.normal(0, 4, size=blurred.shape)
    return np.clip(blurred + noise, 0, 255).astype(np.uint8)


def make_synthetic_sample(rng: np.random.Generator) -> np.ndarray:
    img = make_real_sample(rng).astype(np.float32)

    grid = np.zeros((IMG_SIZE, IMG_SIZE))
    step = int(rng.integers(2, 4))
    grid[::step, ::step] = 1
    checker_strength = rng.uniform(6, 14)
    img += grid[..., None] * checker_strength

    xv, yv = np.meshgrid(np.arange(IMG_SIZE), np.arange(IMG_SIZE))
    freq = rng.uniform(0.25, 0.45)
    phase = rng.uniform(0, 2 * np.pi)
    periodic = 8 * np.sin(2 * np.pi * freq * xv + phase)
    img += periodic[..., None]

    bx, by = rng.integers(0, IMG_SIZE - 16, size=2)
    block = np.clip(img[bx:bx + 16, by:by + 16], 0, 255).astype(np.uint8)
    img[bx:bx + 16, by:by + 16] = _gaussian_blur(block, k=5)

    return np.clip(img, 0, 255).astype(np.uint8)


def generate_dataset(out_dir: str, n_per_class: int, seed: int = 42) -> str:
    os.makedirs(out_dir, exist_ok=True)
    rng = np.random.default_rng(seed)
    records: list[SampleRecord] = []

    for i in range(n_per_class):
        real_img = make_real_sample(rng)
        fname = f"real_{i:04d}.png"
        cv2.imwrite(os.path.join(out_dir, fname), cv2.cvtColor(real_img, cv2.COLOR_RGB2BGR))
        records.append(SampleRecord(fname, "real", seed, "make_real_sample"))

        synth_img = make_synthetic_sample(rng)
        fname = f"synthetic_{i:04d}.png"
        cv2.imwrite(os.path.join(out_dir, fname), cv2.cvtColor(synth_img, cv2.COLOR_RGB2BGR))
        records.append(SampleRecord(fname, "synthetic", seed, "make_synthetic_sample"))

    manifest_path = os.path.join(out_dir, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump([asdict(r) for r in records], f, indent=2)
    return manifest_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "synthetic_media"))
    parser.add_argument("--n", type=int, default=150, help="samples per class")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    manifest = generate_dataset(args.out, args.n, args.seed)
    print(f"Wrote {2 * args.n} samples + manifest to {manifest}")


if __name__ == "__main__":
    main()
