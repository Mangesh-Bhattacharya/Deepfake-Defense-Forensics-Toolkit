# Module A — Synthetic Media Artifact Detection Engine

Maps to job responsibility: *"Detect subtle inconsistencies indicative of AI-generated
or manipulated media across video, audio, and images."*

| File | What it does |
|---|---|
| `image/gan_fingerprint.py` | Extracts an 8-dim frequency/spatial "fingerprint" per image (checkerboard artifacts, spectral peaks, over-smoothing, edge kurtosis, channel-noise correlation, residual entropy). |
| `video/frame_anomaly_scanner.py` | Runs the fingerprint extractor across every frame of a video (or frame directory), scores each frame, and flags frame-to-frame "jitter" typical of face-swap blending seams. |
| `audio/spectrogram_artifact_detector.py` | Numpy-only STFT + cepstral analysis to catch neural-vocoder combing, missing high-frequency energy, and phase-reconstruction artifacts in synthetic speech. |
| `classifier/synthetic_classifier.py` | Trains/evaluates a real (CPU, seconds-to-train) classifier over the fingerprint features on the locally generated dataset; architected with an explicit swap-in point for a real CNN/ViT backbone at scale. |
| `../datasets/generators/synthetic_data_generator.py` | Procedurally generates a local real-vs-synthetic image dataset — no external/scraped data, no licensing risk. |

## Quickstart

```bash
# 1. generate a local synthetic dataset (no internet, no GPU)
python3 datasets/generators/synthetic_data_generator.py --out datasets/synthetic_media --n 150

# 2. train + evaluate the classifier
python3 artifact-detection/classifier/synthetic_classifier.py --model logreg

# 3. inspect a single image's fingerprint
python3 artifact-detection/image/gan_fingerprint.py datasets/synthetic_media/synthetic_0000.png

# 4. scan a directory of frames for temporal anomalies
python3 artifact-detection/video/frame_anomaly_scanner.py datasets/synthetic_media

# 5. compare a real-like vs synthetic-like audio fingerprint
python3 artifact-detection/audio/spectrogram_artifact_detector.py
```

## Why the classifier hits ~100% accuracy on the demo data

The locally generated dataset injects *overt*, well-documented GAN/vocoder artifacts so
the full pipeline is trivially verifiable end-to-end without a GPU or external data. Real
deepfakes are far subtler — see [`docs/ai-safety-evaluation-methodology.md`](../docs/ai-safety-evaluation-methodology.md)
and the "Scaling to production" note in the main README for how this pipeline is designed
to extend to a real CNN/ViT trained on FaceForensics++/DFDC-scale data.
