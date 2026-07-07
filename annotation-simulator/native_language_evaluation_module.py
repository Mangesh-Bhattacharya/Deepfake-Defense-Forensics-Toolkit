"""
native_language_evaluation_module.py
-----------------------------------------
Simulates the "native/fluent-language proficiency" evaluation component
referenced in the job posting for AI Community annotation work — many
deepfake/content-safety annotation tasks require judging culturally- and
linguistically-specific manipulation cues (e.g. voice-cloned speech in a
specific language, or text accompanying a synthetic video) that only a
native/fluent speaker can reliably judge.

This module does NOT ship a real language-proficiency test (that would
require a licensed linguistic assessment). Instead it demonstrates the
*evaluation harness* structure your AI Community submission would plug into:
  1. present a labeling task with target-language text/audio metadata,
  2. collect a language-tagged annotation + a self-reported fluency level,
  3. cross-check the annotation against automated language-ID heuristics
     (character-set / stopword-overlap heuristic — no external API), and
  4. flag mismatches between claimed fluency and task language for review.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict

# Minimal, dependency-free stopword fingerprints for a handful of languages —
# enough to demonstrate the heuristic; swap in a real langid/fastText model
# for production use (see docs/llm-usage-guide.md "swap-in points").
STOPWORD_FINGERPRINTS: Dict[str, set] = {
    "en": {"the", "is", "and", "of", "to", "a", "in", "that", "this"},
    "es": {"el", "la", "de", "que", "y", "en", "un", "es", "por"},
    "fr": {"le", "la", "de", "et", "un", "que", "est", "pour", "dans"},
    "hi": {"है", "और", "के", "में", "की", "यह", "का", "को"},
    "de": {"der", "die", "und", "das", "ist", "ein", "zu", "in"},
}


@dataclass
class LanguageTask:
    task_id: str
    text_sample: str
    declared_language: str


@dataclass
class LanguageEvalResult:
    task_id: str
    declared_language: str
    detected_language: str
    match: bool
    annotator_claimed_fluency: str
    flagged_for_review: bool


def detect_language_heuristic(text: str) -> str:
    tokens = set(text.lower().split())
    best_lang, best_overlap = "unknown", 0
    for lang, stopwords in STOPWORD_FINGERPRINTS.items():
        overlap = len(tokens & stopwords)
        if overlap > best_overlap:
            best_lang, best_overlap = lang, overlap
    return best_lang


def evaluate_task(task: LanguageTask, annotator_claimed_fluency: str) -> LanguageEvalResult:
    detected = detect_language_heuristic(task.text_sample)
    match = detected == task.declared_language
    flag = (not match) or annotator_claimed_fluency.lower() not in ("native", "fluent")
    return LanguageEvalResult(
        task.task_id, task.declared_language, detected, match, annotator_claimed_fluency, flag
    )


DEMO_TASKS = [
    LanguageTask("LT-1", "The synthetic voice in this clip is claiming to be a bank representative.", "en"),
    LanguageTask("LT-2", "El video muestra que el rostro fue alterado digitalmente y es sospechoso.", "es"),
    LanguageTask("LT-3", "यह वीडियो में चेहरा और आवाज़ का मेल संदिग्ध है।", "hi"),
]


if __name__ == "__main__":
    claimed = {"LT-1": "native", "LT-2": "fluent", "LT-3": "conversational"}
    results = [evaluate_task(t, claimed[t.task_id]) for t in DEMO_TASKS]
    print(json.dumps([r.__dict__ for r in results], indent=2, ensure_ascii=False))
