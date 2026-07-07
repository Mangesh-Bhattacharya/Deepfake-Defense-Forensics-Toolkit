"""Integration test: fingerprint -> ForensicCase -> Markdown report -> PDF ->
evidence bundle, exercised end-to-end."""
import os

from report_generator import build_case_from_classifier, save_report, render_markdown
from pdf_report import render_pdf
from evidence_packaging import package_evidence, verify_bundle
from chain_of_custody import ChainOfCustodyLog, sha256_of_bytes


def test_full_forensic_pipeline(tmp_path):
    fingerprint = {
        "high_freq_energy_ratio": 0.09, "checkerboard_score": 0.7, "spectral_peak_count": 5,
        "edge_sharpness_kurtosis": 3.1, "color_channel_corr": 0.5,
    }
    case = build_case_from_classifier(
        "CASE-TEST", "test_evidence.png", "pytest", "Integration test evidence.",
        fingerprint, classifier_pred=1, classifier_score=0.9,
    )
    assert case.overall_verdict == "LIKELY_SYNTHETIC"
    assert len(case.markers) > 0

    md_path = save_report(case, str(tmp_path))
    assert os.path.exists(md_path)
    assert "CASE-TEST" in render_markdown(case)

    pdf_path = render_pdf(case, str(tmp_path / "report.pdf"))
    assert os.path.exists(pdf_path)
    assert os.path.getsize(pdf_path) > 0

    log = ChainOfCustodyLog(str(tmp_path / "custody.jsonl"))
    log.add_entry("pytest", "INGEST", "CASE-TEST", sha256_of_bytes(b"evidence-bytes"))
    assert log.verify_chain() is True

    bundle_path = package_evidence("CASE-TEST", [md_path, pdf_path], str(tmp_path))
    assert os.path.exists(bundle_path)
    assert verify_bundle(bundle_path) is True
