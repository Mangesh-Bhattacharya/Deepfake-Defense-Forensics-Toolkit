"""
qualification_exam_simulator.py
------------------------------------
Simulates the kind of qualification/assessment exam referenced in the job
posting ("assessment requirement") that AI Community platforms typically use
to certify an analyst before granting access to live annotation queues.

Contains a bank of deepfake-detection / digital-forensics domain-knowledge
questions, administers a randomized subset, scores the result, and applies a
pass/fail policy consistent with typical AI Community qualification bars
(usually 80%+).
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class ExamQuestion:
    id: str
    prompt: str
    choices: List[str]
    correct_index: int
    topic: str


QUESTION_BANK: List[ExamQuestion] = [
    ExamQuestion("Q1", "Checkerboard artifacts in a generated image are most commonly caused by:",
                 ["JPEG compression", "Transposed-convolution upsampling in GAN generators",
                  "Camera sensor noise", "Lens distortion"], 1, "artifact-detection"),
    ExamQuestion("Q2", "A high Population Stability Index (PSI > 0.25) between a baseline and new "
                       "data batch indicates:",
                 ["The model is perfectly calibrated", "No action needed",
                  "A major distribution shift — investigate/retrain", "A labeling error"], 2, "ai-safety"),
    ExamQuestion("Q3", "In a face-recognition liveness check, a 'looped video' presentation attack is "
                       "hardest to catch using which single signal alone?",
                 ["Motion energy", "Periodicity/autocorrelation of motion", "Eye-blink texture cue",
                  "Skin reflectance"], 0, "biometrics"),
    ExamQuestion("Q4", "Chain-of-custody hashing in a forensic pipeline primarily protects against:",
                 ["Slow processing", "Undetected evidence tampering after collection",
                  "Poor image quality", "Model overfitting"], 1, "forensics"),
    ExamQuestion("Q5", "Fleiss' Kappa is used to measure:",
                 ["Classifier accuracy", "Agreement among 3+ annotators beyond chance",
                  "Model robustness to noise", "Dataset size"], 1, "annotation"),
    ExamQuestion("Q6", "Why do neural vocoders (TTS/voice-cloning) often under-represent energy above ~8kHz?",
                 ["Microphones can't record it", "Many vocoder architectures band-limit / smooth "
                  "high-frequency reconstruction", "It's a copyright protection measure",
                  "Human ears can't hear it"], 1, "audio-forensics"),
    ExamQuestion("Q7", "A safety-critical deepfake gate should typically optimize its decision threshold to:",
                 ["Maximize raw accuracy only", "Minimize false negatives subject to an acceptable "
                  "false-positive rate", "Always block everything", "Ignore threshold tuning"], 1, "ai-safety"),
    ExamQuestion("Q8", "Which of these is NOT one of the four essentials of responsible LLM-assisted "
                       "forensic reporting used in this toolkit?",
                 ["Human-in-the-loop sign-off", "Traceability of every claim to structured evidence",
                  "Letting the LLM invent new manipulation markers freely", "Clear labeling of "
                  "LLM-authored narrative sections"], 2, "llm-safety"),
]


def administer_exam(n_questions: int = 6, seed: int | None = None, pass_threshold: float = 0.8) -> dict:
    rng = random.Random(seed)
    questions = rng.sample(QUESTION_BANK, k=min(n_questions, len(QUESTION_BANK)))

    # Simulated "correct" respondent answers for a self-contained demo run
    # (in real use, replace `simulated_answers` with actual human input capture)
    simulated_answers = {q.id: q.correct_index for q in questions}

    correct = sum(1 for q in questions if simulated_answers[q.id] == q.correct_index)
    score = correct / len(questions)
    passed = score >= pass_threshold

    topic_breakdown: Dict[str, List[str]] = {}
    for q in questions:
        topic_breakdown.setdefault(q.topic, []).append(q.id)

    return {
        "n_questions": len(questions),
        "correct": correct,
        "score": round(score, 3),
        "pass_threshold": pass_threshold,
        "passed": passed,
        "topics_covered": topic_breakdown,
    }


if __name__ == "__main__":
    result = administer_exam(n_questions=6, seed=42)
    print(json.dumps(result, indent=2))
