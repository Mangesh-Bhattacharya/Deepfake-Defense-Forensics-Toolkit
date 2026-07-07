"""
pdf_report.py
----------------
Renders a ForensicCase (see report_generator.py) as a polished PDF summary
using reportlab (pure-Python, no external binary dependency like wkhtmltopdf).
"""
from __future__ import annotations

import os
import sys
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable)

sys.path.append(os.path.dirname(__file__))
from report_generator import ForensicCase  # noqa: E402


def render_pdf(case: ForensicCase, out_path: str, llm_narrative: Optional[str] = None) -> str:
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    doc = SimpleDocTemplate(out_path, pagesize=LETTER, topMargin=0.6 * inch, bottomMargin=0.6 * inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleX", parent=styles["Title"], fontSize=18, spaceAfter=6)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], spaceBefore=14, spaceAfter=6)
    body = styles["BodyText"]

    story = [
        Paragraph(f"Digital Forensic Report — Case {case.case_id}", title_style),
        Paragraph(f"Generated (UTC): {case.generated_at}", body),
        HRFlowable(width="100%", color=colors.grey),
        Spacer(1, 10),
    ]

    meta_table = Table([
        ["Evidence ID", case.evidence_id],
        ["Analyst", case.analyst],
        ["Overall verdict", case.overall_verdict],
        ["Overall confidence", f"{case.overall_confidence:.0%}"],
    ], colWidths=[150, 350])
    meta_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    story.append(meta_table)

    story.append(Paragraph("Evidence Description", h2))
    story.append(Paragraph(case.evidence_description, body))

    story.append(Paragraph("Manipulation Markers Detected", h2))
    if case.markers:
        data = [["Marker", "Confidence", "Detail"]]
        for m in case.markers:
            data.append([m.marker_type, f"{m.confidence:.0%}", m.detail])
        t = Table(data, colWidths=[110, 70, 320])
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(t)
    else:
        story.append(Paragraph("No manipulation markers exceeded detection thresholds.", body))

    if llm_narrative:
        story.append(Paragraph("LLM-Assisted Narrative Summary", h2))
        story.append(Paragraph(
            "Drafted by a local LLM from the structured findings above; requires analyst sign-off.",
            ParagraphStyle("italic", parent=body, fontName="Helvetica-Oblique", fontSize=8)))
        story.append(Spacer(1, 4))
        story.append(Paragraph(llm_narrative.replace("\n", "<br/>"), body))

    story.append(Paragraph("Disclaimer", h2))
    story.append(Paragraph(
        "This report is produced by an automated toolkit for training/demonstration purposes. "
        "It does not constitute a certified forensic opinion. A qualified human analyst must "
        "review and countersign before this report is used in any legal, HR, or compliance context.",
        ParagraphStyle("disclaimer", parent=body, fontSize=8, textColor=colors.grey)))

    doc.build(story)
    return out_path


if __name__ == "__main__":
    from report_generator import build_case_from_classifier
    demo_case = build_case_from_classifier(
        "CASE-DEMO", "demo_evidence.png", "automated-pipeline",
        "Demo still image submitted for synthetic-media forensic analysis.",
        {"high_freq_energy_ratio": 0.09, "checkerboard_score": 0.7, "spectral_peak_count": 5,
         "edge_sharpness_kurtosis": 3.1, "color_channel_corr": 0.5},
        classifier_pred=1, classifier_score=0.93,
    )
    out = render_pdf(demo_case, os.path.join(os.path.dirname(__file__), "..", "docs", "sample-reports", "CASE-DEMO_forensic_report.pdf"))
    print(f"PDF written to {out}")
