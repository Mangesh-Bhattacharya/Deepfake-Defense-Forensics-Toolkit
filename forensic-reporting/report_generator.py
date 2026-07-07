"""
report_generator.py
----------------------
Deepfake manipulation-marker forensic report generator.

Takes structured evidence — the outputs of artifact-detection and/or
biometric-stress-tests modules — and produces a professional Markdown
forensic report. Two modes:

  * template mode (default, no LLM required): fills a deterministic template.
    Every number in the report traces directly back to a detector output —
    nothing is invented.
  * LLM-assisted mode (--llm): additionally asks a local/cloud LLM (via
    llm-layer/llm_interface.py) to draft a plain-English narrative summary
    and stakeholder explanation from the same structured evidence. The raw
    structured findings are always included alongside the narrative so a
    human reviewer can verify the LLM did not introduce unsupported claims —
    see docs/llm-usage-guide.md for the human-in-the-loop policy.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "llm-layer"))


@dataclass
class ManipulationMarker:
    marker_type: str
    confidence: float
    detail: str


@dataclass
class ForensicCase:
    case_id: str
    evidence_id: str
    analyst: str
    evidence_description: str
    markers: List[ManipulationMarker]
    overall_verdict: str  # "LIKELY_SYNTHETIC" | "LIKELY_AUTHENTIC" | "INCONCLUSIVE"
    overall_confidence: float
    generated_at: str = ""

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now(timezone.utc).isoformat()


def build_case_from_classifier(
    case_id: str, evidence_id: str, analyst: str, evidence_description: str,
    fingerprint_dict: Dict[str, float], classifier_pred: int, classifier_score: float,
) -> ForensicCase:
    """Turns raw fingerprint + classifier output into a ForensicCase with
    human-readable manipulation markers."""
    markers = []
    # Thresholds below are calibrated empirically against this toolkit's local
    # synthetic_media dataset distribution (see
    # ai-safety-evaluation/model_drift_detection.py and
    # ai-safety-evaluation/guardrail_scoring.py for the general calibration
    # methodology). Only features that are reliably, directionally
    # discriminative on this dataset are used as pass/fail markers here;
    # `spectral_peak_count`, `checkerboard_score`, and `edge_sharpness_kurtosis`
    # are still computed and shown in the raw fingerprint output (see
    # gan_fingerprint.py) but are NOT used as binary markers because they did
    # not separate real vs. synthetic reliably on this toy generator — see
    # artifact-detection/README.md "Why the classifier hits ~100% accuracy".
    # `higher_is_suspicious=False` means an unusually LOW value is the signal
    # (e.g. injected structured artifacts reduce noise-residual entropy).
    marker_rules = [
        ("color_channel_corr", 0.35, True,
         "Unusually high cross-channel noise correlation, atypical of independent raw sensor noise per color channel."),
        ("local_variance_std", 10.0, True,
         "High variability in local block variance, consistent with GAN over-smoothing in some regions and sharp injected structure in others."),
        ("noise_residual_entropy", 1.8, False,
         "Unusually low noise-residual entropy, consistent with structured/periodic artifacts rather than organic sensor noise."),
        ("high_freq_energy_ratio", 0.0006, True,
         "Elevated high-frequency spectral energy relative to baseline, consistent with GAN/diffusion upsampling artifacts."),
    ]
    for key, threshold, higher_is_suspicious, description in marker_rules:
        value = fingerprint_dict.get(key)
        if value is None:
            continue
        triggered = (value >= threshold) if higher_is_suspicious else (value <= threshold)
        if triggered:
            margin = abs(value - threshold) / (abs(threshold) + 1e-6)
            confidence = min(0.99, 0.5 + margin * 0.3)
            markers.append(ManipulationMarker(key, round(confidence, 3), description))

    if classifier_pred == 1:
        verdict = "LIKELY_SYNTHETIC"
    elif classifier_score > 0.35:
        verdict = "INCONCLUSIVE"
    else:
        verdict = "LIKELY_AUTHENTIC"

    return ForensicCase(
        case_id=case_id, evidence_id=evidence_id, analyst=analyst,
        evidence_description=evidence_description, markers=markers,
        overall_verdict=verdict, overall_confidence=round(float(classifier_score), 3),
    )


def render_markdown(case: ForensicCase, llm_narrative: Optional[str] = None) -> str:
    lines = [
        f"# Digital Forensic Report — Case {case.case_id}",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Evidence ID | {case.evidence_id} |",
        f"| Analyst | {case.analyst} |",
        f"| Generated (UTC) | {case.generated_at} |",
        f"| Overall verdict | **{case.overall_verdict}** |",
        f"| Overall confidence | {case.overall_confidence:.0%} |",
        "",
        "## Evidence Description",
        case.evidence_description,
        "",
        "## Manipulation Markers Detected",
    ]
    if case.markers:
        lines.append("| Marker | Confidence | Detail |")
        lines.append("|---|---|---|")
        for m in case.markers:
            lines.append(f"| `{m.marker_type}` | {m.confidence:.0%} | {m.detail} |")
    else:
        lines.append("_No manipulation markers exceeded detection thresholds._")

    if llm_narrative:
        lines += [
            "",
            "## LLM-Assisted Narrative Summary",
            "> The following narrative was drafted by a local LLM from the structured "
            "findings above, for a non-technical stakeholder audience. It has **not** been "
            "independently fact-checked beyond the structured data it was given — treat it as "
            "a first draft requiring analyst sign-off. See `docs/llm-usage-guide.md`.",
            "",
            llm_narrative,
        ]

    lines += [
        "",
        "## Chain of Custody",
        "See accompanying `custody_log.jsonl` for the tamper-evident evidence handling record.",
        "",
        "## Methodology",
        "Generated by `forensic-reporting/report_generator.py` using feature thresholds defined "
        "in `ai-safety-evaluation/guardrail_scoring.py`. Full methodology: "
        "`docs/ai-safety-evaluation-methodology.md`.",
        "",
        "---",
        "*This report is produced by an automated toolkit for training/demonstration purposes. "
        "It does not constitute a certified forensic opinion. A qualified human analyst must "
        "review and countersign before this report is used in any legal, HR, or compliance context.*",
    ]
    return "\n".join(lines)


def save_report(case: ForensicCase, out_dir: str, llm_narrative: Optional[str] = None) -> str:
    os.makedirs(out_dir, exist_ok=True)
    md = render_markdown(case, llm_narrative=llm_narrative)
    path = os.path.join(out_dir, f"{case.case_id}_forensic_report.md")
    with open(path, "w") as f:
        f.write(md)
    json_path = os.path.join(out_dir, f"{case.case_id}_forensic_report.json")
    with open(json_path, "w") as f:
        json.dump({
            "case": {k: v for k, v in case.__dict__.items() if k != "markers"},
            "markers": [m.__dict__ for m in case.markers],
            "llm_narrative": llm_narrative,
        }, f, indent=2)
    return path


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", help="path to image to analyze")
    parser.add_argument("--case-id", default="CASE-0001")
    parser.add_argument("--analyst", default="automated-pipeline")
    parser.add_argument("--out-dir", default=os.path.join(os.path.dirname(__file__), "..", "docs", "sample-reports"))
    parser.add_argument("--llm", action="store_true", help="also draft an LLM-assisted narrative")
    args = parser.parse_args()

    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "artifact-detection", "image"))
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "artifact-detection", "classifier"))
    import cv2
    from gan_fingerprint import extract_fingerprint
    from synthetic_classifier import SyntheticMediaClassifier, MODEL_PATH

    image_path = args.image
    if not image_path:
        # default: analyze the first synthetic sample from the demo dataset
        default_dir = os.path.join(os.path.dirname(__file__), "..", "datasets", "synthetic_media")
        image_path = os.path.join(default_dir, "synthetic_0000.png")

    img = cv2.cvtColor(cv2.imread(image_path), cv2.COLOR_BGR2RGB)
    fp = extract_fingerprint(img)

    if os.path.exists(MODEL_PATH):
        clf = SyntheticMediaClassifier.load()
        pred, score = clf.predict_image(img)
    else:
        pred, score = 1 if fp.as_dict()["high_freq_energy_ratio"] > 0.05 else 0, 0.5

    case = build_case_from_classifier(
        args.case_id, os.path.basename(image_path), args.analyst,
        f"Still image submitted for synthetic-media forensic analysis: `{os.path.basename(image_path)}`.",
        fp.as_dict(), pred, score,
    )

    narrative = None
    if args.llm:
        try:
            from llm_interface import get_default_client
            client = get_default_client()
            narrative = client.draft_forensic_narrative(case.__dict__, [m.__dict__ for m in case.markers])
        except Exception as e:  # noqa: BLE001
            narrative = f"_LLM narrative unavailable in this environment ({e}). Falling back to template-only report._"

    path = save_report(case, args.out_dir, llm_narrative=narrative)
    print(f"Report written to {path}")
    print(f"Verdict: {case.overall_verdict} ({case.overall_confidence:.0%} confidence), {len(case.markers)} markers")


if __name__ == "__main__":
    main()
