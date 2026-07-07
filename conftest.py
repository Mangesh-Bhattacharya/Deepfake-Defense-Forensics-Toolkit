"""Root pytest conftest: adds every module directory to sys.path so tests can
import scripts directly by filename (folder names use hyphens and are not
valid Python package names, matching the repo-structure spec)."""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

MODULE_DIRS = [
    "artifact-detection/image",
    "artifact-detection/video",
    "artifact-detection/audio",
    "artifact-detection/classifier",
    "biometric-stress-tests",
    "forensic-reporting",
    "ai-safety-evaluation",
    "annotation-simulator",
    "llm-layer",
    "datasets/generators",
]

for rel in MODULE_DIRS:
    path = os.path.join(ROOT, rel)
    if path not in sys.path:
        sys.path.insert(0, path)
