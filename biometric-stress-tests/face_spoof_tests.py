"""
face_spoof_tests.py
---------------------
Face-recognition spoofing test battery.

Simulates common presentation-attack vectors against a face recognition /
face-matching component, WITHOUT needing a real face-recognition model or
biometric database — it operates on any embedding function you supply
(defaults to a lightweight local HOG-like embedding for self-contained runs).

Attack types implemented:
  1. print_attack        - simulates a flat printed photo (loses high-freq detail + adds paper texture)
  2. replay_attack       - simulates a screen replay (moire pattern + backlight halo + slight blur)
  3. mask_attack         - simulates a 3D mask (color desaturation + edge over-sharpness at seams)
  4. morph_attack        - simulates a face-morph between two identities (alpha blend)
  5. adversarial_patch   - adds a small adversarial-style high-frequency patch to a region

Each test perturbs a "genuine" probe image and measures whether a similarity
function still (wrongly) matches it to the enrolled identity above a
threshold — i.e. whether the spoof would fool the system.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List

import numpy as np
import cv2


Embedder = Callable[[np.ndarray], np.ndarray]


def default_embedder(img: np.ndarray) -> np.ndarray:
    """Lightweight local stand-in for a real face-recognition embedding
    (e.g. ArcFace/FaceNet). Uses HOG since it is deterministic, dependency-free,
    and sensitive to the same class of perturbations (texture/edge structure)
    the attacks below manipulate. Swap this for a real embedding model in
    production — see docs/llm-usage-guide.md 'swap-in points'."""
    gray = cv2.cvtColor(cv2.resize(img, (64, 64)), cv2.COLOR_RGB2GRAY)
    hog = cv2.HOGDescriptor(
        _winSize=(64, 64), _blockSize=(16, 16), _blockStride=(8, 8), _cellSize=(8, 8), _nbins=9
    )
    return hog.compute(gray).flatten()


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-8
    return float(np.dot(a, b) / denom)


def print_attack(img: np.ndarray) -> np.ndarray:
    out = cv2.GaussianBlur(img, (3, 3), 0).astype(np.float32)
    texture = np.random.default_rng(1).normal(0, 6, size=out.shape)
    out = np.clip(out * 0.9 + texture, 0, 255).astype(np.uint8)
    return out


def replay_attack(img: np.ndarray) -> np.ndarray:
    h, w = img.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    moire = 10 * np.sin(0.5 * xx) * np.sin(0.5 * yy)
    halo = np.zeros((h, w))
    cy, cx = h // 2, w // 4
    r = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    halo += np.clip(40 - r, 0, 40)
    out = img.astype(np.float32) + moire[..., None] + halo[..., None] * 0.3
    out = cv2.GaussianBlur(np.clip(out, 0, 255).astype(np.uint8), (3, 3), 0)
    return out


def mask_attack(img: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV).astype(np.float32)
    hsv[..., 1] *= 0.5  # desaturate (silicone/resin mask look)
    out = cv2.cvtColor(np.clip(hsv, 0, 255).astype(np.uint8), cv2.COLOR_HSV2RGB)
    edges = cv2.Canny(out, 80, 160)
    out[edges > 0] = np.clip(out[edges > 0].astype(np.int32) + 30, 0, 255).astype(np.uint8)
    return out


def morph_attack(img_a: np.ndarray, img_b: np.ndarray, alpha: float = 0.5) -> np.ndarray:
    a = cv2.resize(img_a, (img_b.shape[1], img_b.shape[0]))
    return cv2.addWeighted(a, alpha, img_b, 1 - alpha, 0)


def adversarial_patch(img: np.ndarray, patch_size: int = 12, strength: float = 60.0) -> np.ndarray:
    out = img.copy().astype(np.float32)
    h, w = out.shape[:2]
    rng = np.random.default_rng(7)
    py, px = h // 2 - patch_size // 2, w // 2 - patch_size // 2
    patch = rng.uniform(-strength, strength, size=(patch_size, patch_size, out.shape[2]))
    out[py:py + patch_size, px:px + patch_size] += patch
    return np.clip(out, 0, 255).astype(np.uint8)


@dataclass
class SpoofTestResult:
    attack_name: str
    similarity_to_genuine: float
    match_threshold: float
    fooled_system: bool


ATTACKS: Dict[str, Callable] = {
    "print_attack": print_attack,
    "replay_attack": replay_attack,
    "mask_attack": mask_attack,
    "adversarial_patch": adversarial_patch,
}


def run_spoof_battery(
    genuine_enrolled: np.ndarray,
    genuine_probe: np.ndarray,
    embedder: Embedder = default_embedder,
    match_threshold: float = 0.85,
) -> List[SpoofTestResult]:
    """Runs every attack in ATTACKS against `genuine_probe`, compares each
    spoofed embedding to the `genuine_enrolled` embedding, and reports whether
    the spoof would be wrongly matched (fool the system)."""
    enrolled_emb = embedder(genuine_enrolled)
    results = []
    for name, attack_fn in ATTACKS.items():
        spoofed = attack_fn(genuine_probe)
        spoofed_emb = embedder(spoofed)
        sim = cosine_similarity(enrolled_emb, spoofed_emb)
        results.append(SpoofTestResult(name, sim, match_threshold, sim >= match_threshold))
    # morph is 2-image so handled separately
    return results


def run_morph_test(
    img_a: np.ndarray, img_b: np.ndarray, embedder: Embedder = default_embedder, match_threshold: float = 0.85
) -> SpoofTestResult:
    morphed = morph_attack(img_a, img_b)
    emb_a = embedder(img_a)
    emb_morph = embedder(morphed)
    sim = cosine_similarity(emb_a, emb_morph)
    return SpoofTestResult("morph_attack", sim, match_threshold, sim >= match_threshold)


if __name__ == "__main__":
    rng = np.random.default_rng(0)
    fake_face = (rng.normal(140, 20, (64, 64, 3))).clip(0, 255).astype(np.uint8)
    fake_face2 = (rng.normal(120, 20, (64, 64, 3))).clip(0, 255).astype(np.uint8)

    results = run_spoof_battery(fake_face, fake_face)
    results.append(run_morph_test(fake_face, fake_face2))
    for r in results:
        status = "FOOLED SYSTEM" if r.fooled_system else "blocked"
        print(f"{r.attack_name:20s} sim={r.similarity_to_genuine:.3f}  threshold={r.match_threshold}  -> {status}")
