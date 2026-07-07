"""
stress_test_dashboard.py
---------------------------
Aggregates results from face_spoof_tests.py, voice_adversarial_generator.py,
and liveness_bypass_tests.py into a single stress-test scoring dashboard,
rendered as both a JSON summary (for CI/automation) and a self-contained
HTML report (for human review).

Vulnerability Score = (# attacks that fooled the system) / (# attacks run),
reported per subsystem (face / voice / liveness) and overall. Lower is better.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import List

import numpy as np

sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "artifact-detection", "audio"))

from face_spoof_tests import run_spoof_battery, run_morph_test  # noqa: E402
from voice_adversarial_generator import run_voice_attack_battery  # noqa: E402
from liveness_bypass_tests import run_liveness_bypass_battery  # noqa: E402
from spectrogram_artifact_detector import make_real_speech_like  # noqa: E402


@dataclass
class SubsystemScore:
    subsystem: str
    total_attacks: int
    successful_attacks: int
    vulnerability_score: float
    details: List[dict]


@dataclass
class DashboardReport:
    generated_at: str
    subsystems: List[SubsystemScore]
    overall_vulnerability_score: float

    def to_dict(self) -> dict:
        return {
            "generated_at": self.generated_at,
            "overall_vulnerability_score": round(self.overall_vulnerability_score, 4),
            "subsystems": [asdict(s) for s in self.subsystems],
        }


def run_all_stress_tests(seed: int = 0) -> DashboardReport:
    rng = np.random.default_rng(seed)

    # --- Face subsystem ---
    face_img = rng.normal(140, 20, (64, 64, 3)).clip(0, 255).astype(np.uint8)
    face_img2 = rng.normal(120, 20, (64, 64, 3)).clip(0, 255).astype(np.uint8)
    face_results = run_spoof_battery(face_img, face_img)
    face_results.append(run_morph_test(face_img, face_img2))
    face_success = sum(1 for r in face_results if r.fooled_system)
    face_score = SubsystemScore(
        "face_recognition", len(face_results), face_success,
        face_success / len(face_results),
        [asdict(r) for r in face_results],
    )

    # --- Voice subsystem ---
    enrolled = make_real_speech_like(rng)
    probe = make_real_speech_like(rng)
    voice_results = run_voice_attack_battery(enrolled, probe)
    voice_success = sum(1 for r in voice_results if r.fooled_system)
    voice_score = SubsystemScore(
        "voice_recognition", len(voice_results), voice_success,
        voice_success / len(voice_results),
        [asdict(r) for r in voice_results],
    )

    # --- Liveness subsystem ---
    liveness_results = [r for r in run_liveness_bypass_battery(seed) if r.technique != "genuine_live"]
    liveness_success = sum(1 for r in liveness_results if r.bypassed)
    liveness_score = SubsystemScore(
        "liveness_detection", len(liveness_results), liveness_success,
        liveness_success / len(liveness_results),
        [asdict(r) for r in liveness_results],
    )

    subsystems = [face_score, voice_score, liveness_score]
    total_attacks = sum(s.total_attacks for s in subsystems)
    total_success = sum(s.successful_attacks for s in subsystems)
    overall = total_success / total_attacks if total_attacks else 0.0

    return DashboardReport(datetime.now(timezone.utc).isoformat(), subsystems, overall)


def render_html(report: DashboardReport) -> str:
    rows = ""
    for s in report.subsystems:
        rows += f"""
        <tr>
          <td>{s.subsystem}</td>
          <td>{s.total_attacks}</td>
          <td>{s.successful_attacks}</td>
          <td style="color:{'#c0392b' if s.vulnerability_score > 0.5 else '#e67e22' if s.vulnerability_score > 0 else '#27ae60'}">
            {s.vulnerability_score:.0%}
          </td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Biometric Stress-Test Dashboard</title>
<style>
body {{ font-family: -apple-system, Arial, sans-serif; margin: 40px; background:#0f1115; color:#e6e6e6; }}
h1 {{ color:#fff; }}
table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
th, td {{ border: 1px solid #333; padding: 10px; text-align: left; }}
th {{ background:#1b1e26; }}
.summary {{ font-size: 1.4em; margin: 20px 0; }}
</style></head>
<body>
<h1>Biometric Stress-Test Scoring Dashboard</h1>
<p>Generated: {report.generated_at}</p>
<div class="summary">Overall vulnerability score: <b>{report.overall_vulnerability_score:.0%}</b>
(fraction of simulated attacks that successfully fooled a subsystem)</div>
<table>
<tr><th>Subsystem</th><th>Attacks run</th><th>Successful attacks</th><th>Vulnerability score</th></tr>
{rows}
</table>
<p style="margin-top:30px;color:#888;font-size:0.9em;">
This dashboard uses lightweight, dependency-free stand-in embeddings/liveness heuristics
(see biometric-stress-tests/*.py docstrings) so it runs end-to-end without a GPU or a real
biometric SDK. Vulnerability findings here demonstrate the *methodology*; production use
requires re-running this battery against the real deployed embedding/liveness models.
</p>
</body></html>"""


def main():
    report = run_all_stress_tests()
    out_dir = os.path.join(os.path.dirname(__file__), "..", "docs")
    os.makedirs(out_dir, exist_ok=True)

    json_path = os.path.join(out_dir, "stress_test_report.json")
    with open(json_path, "w") as f:
        json.dump(report.to_dict(), f, indent=2)

    html_path = os.path.join(out_dir, "stress_test_dashboard.html")
    with open(html_path, "w") as f:
        f.write(render_html(report))

    print(json.dumps(report.to_dict(), indent=2))
    print(f"\nHTML dashboard written to {html_path}")


if __name__ == "__main__":
    main()
