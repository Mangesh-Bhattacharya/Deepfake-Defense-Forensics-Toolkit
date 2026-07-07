"""
spectrogram_artifact_detector.py
----------------------------------
Audio spectrogram artifact detector for synthetic / voice-cloned speech.

Neural TTS and voice-conversion vocoders (WaveNet, HiFi-GAN, WaveGlow, etc.)
leave detectable traces in the spectrogram:
  * unnaturally regular harmonic spacing / metallic periodicity from
    neural vocoder upsampling ("comb filtering" artifacts)
  * abnormally low high-frequency energy (vocoders often under-model >8kHz
    content relative to real microphone recordings)
  * unusually flat spectral-flux over time (real speech has more micro-variation)
  * phase discontinuities at frame boundaries (many vocoders are
    magnitude-only and reconstruct phase, which is imperfect)

This module has **no dependency on librosa** (kept out of requirements to
stay lightweight/CPU-only) — it implements STFT with numpy and derives the
same class of features librosa would give you.

Works on raw 1-D numpy waveforms (float32, [-1, 1]) sampled at any rate; a
synthetic waveform generator is included for self-contained demos/tests.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import numpy as np


@dataclass
class AudioFingerprint:
    features: List[float]
    feature_names: List[str] = field(default_factory=lambda: [
        "harmonic_regularity",
        "high_freq_energy_ratio",
        "spectral_flux_std",
        "phase_discontinuity_score",
        "comb_filter_score",
    ])

    def as_dict(self) -> dict:
        return dict(zip(self.feature_names, self.features))


def stft(signal: np.ndarray, n_fft: int = 512, hop: int = 128) -> np.ndarray:
    window = np.hanning(n_fft)
    n_frames = 1 + (len(signal) - n_fft) // hop
    if n_frames <= 0:
        signal = np.pad(signal, (0, n_fft - len(signal)))
        n_frames = 1
    frames = np.stack([
        signal[i * hop: i * hop + n_fft] * window
        for i in range(n_frames)
        if i * hop + n_fft <= len(signal)
    ]) if n_frames > 0 else np.zeros((1, n_fft))
    spec = np.fft.rfft(frames, axis=1)
    return spec  # complex, shape (n_frames, n_fft//2+1)


def _harmonic_regularity(mag: np.ndarray) -> float:
    """Autocorrelation of the mean magnitude spectrum across frequency bins:
    high regularity => suspiciously periodic harmonic comb (vocoder artifact)."""
    mean_spec = mag.mean(axis=0)
    mean_spec = mean_spec - mean_spec.mean()
    if mean_spec.std() < 1e-8:
        return 0.0
    autocorr = np.correlate(mean_spec, mean_spec, mode="full")
    autocorr = autocorr[len(autocorr) // 2:]
    autocorr /= (autocorr[0] + 1e-8)
    # look for a strong secondary peak (periodicity), ignoring lag 0
    return float(np.max(autocorr[3:20])) if len(autocorr) > 20 else 0.0


def _high_freq_energy_ratio(mag: np.ndarray) -> float:
    n_bins = mag.shape[1]
    hi_start = int(n_bins * 0.75)
    total = mag.sum() + 1e-8
    return float(mag[:, hi_start:].sum() / total)


def _spectral_flux_std(mag: np.ndarray) -> float:
    if mag.shape[0] < 2:
        return 0.0
    flux = np.sqrt(np.sum(np.diff(mag, axis=0) ** 2, axis=1))
    return float(flux.std())


def _phase_discontinuity(spec: np.ndarray) -> float:
    phase = np.angle(spec)
    if phase.shape[0] < 2:
        return 0.0
    diffs = np.diff(phase, axis=0)
    wrapped = np.angle(np.exp(1j * diffs))
    return float(np.mean(np.abs(wrapped)))


def _comb_filter_score(mag: np.ndarray) -> float:
    """Real-cepstrum peak strength — a strong low-quefrency peak indicates
    strong periodic combing consistent with neural-vocoder upsampling."""
    log_mag = np.log(mag.mean(axis=0) + 1e-8)
    cepstrum = np.fft.irfft(log_mag)
    if len(cepstrum) < 10:
        return 0.0
    body = cepstrum[3:len(cepstrum) // 2]
    if len(body) == 0 or body.std() < 1e-8:
        return 0.0
    z = (body.max() - body.mean()) / (body.std() + 1e-8)
    return float(z)


def extract_audio_fingerprint(signal: np.ndarray, n_fft: int = 512, hop: int = 128) -> AudioFingerprint:
    spec = stft(signal, n_fft=n_fft, hop=hop)
    mag = np.abs(spec)
    features = [
        _harmonic_regularity(mag),
        _high_freq_energy_ratio(mag),
        _spectral_flux_std(mag),
        _phase_discontinuity(spec),
        _comb_filter_score(mag),
    ]
    return AudioFingerprint(features=features)


def make_real_speech_like(rng: np.random.Generator, sr: int = 16000, dur: float = 1.0) -> np.ndarray:
    """Synthesize a toy 'organic' waveform: a few slightly-drifting harmonics + noise,
    approximating natural micro-variation in real speech."""
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    f0 = 120 + rng.normal(0, 3)
    sig = np.zeros_like(t)
    for k in range(1, 6):
        drift = rng.normal(0, 0.5, size=t.shape).cumsum() * 0.001
        sig += (1.0 / k) * np.sin(2 * np.pi * k * f0 * t + drift)
    sig += rng.normal(0, 0.02, size=t.shape)
    return (sig / (np.max(np.abs(sig)) + 1e-8)).astype(np.float32)


def make_synthetic_speech_like(rng: np.random.Generator, sr: int = 16000, dur: float = 1.0) -> np.ndarray:
    """Synthesize a toy 'vocoder-like' waveform: perfectly periodic harmonics
    (no drift), truncated high-frequency band, and comb-filter structure."""
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    f0 = 120.0
    sig = np.zeros_like(t)
    for k in range(1, 6):
        sig += (1.0 / k) * np.sin(2 * np.pi * k * f0 * t)  # perfectly periodic, no drift
    # simulate low-pass vocoder rolloff by smoothing
    kernel = np.ones(5) / 5
    sig = np.convolve(sig, kernel, mode="same")
    sig += rng.normal(0, 0.005, size=t.shape)  # unnaturally clean noise floor
    return (sig / (np.max(np.abs(sig)) + 1e-8)).astype(np.float32)


if __name__ == "__main__":
    rng = np.random.default_rng(0)
    real = make_real_speech_like(rng)
    synth = make_synthetic_speech_like(rng)
    print("REAL   :", extract_audio_fingerprint(real).as_dict())
    print("SYNTH  :", extract_audio_fingerprint(synth).as_dict())
