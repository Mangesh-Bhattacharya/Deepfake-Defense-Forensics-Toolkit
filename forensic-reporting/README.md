# Module C — Digital Forensics Reporting Framework

Maps to job responsibility: *"Produce clear forensic reports documenting manipulation
markers found in synthetic media, with defensible chain-of-custody."*

| File | What it does |
|---|---|
| `report_generator.py` | Turns artifact-detection output into a `ForensicCase` and renders a Markdown + JSON report, optionally with an LLM-drafted narrative. |
| `pdf_report.py` | Renders the same case as a polished PDF (reportlab, no external binary deps). |
| `chain_of_custody.py` | Tamper-evident, hash-chained JSON-lines custody log (append-only, independently verifiable). |
| `evidence_packaging.py` | Zips report + evidence into a bundle with a SHA-256 manifest; `verify_bundle()` re-checks integrity. |
| `templates/forensic_report_template.md` | The underlying report template (also documented in `docs/forensic-report-templates.md`, including the LLM-assisted variant). |

## Run the full reporting pipeline end-to-end

```bash
python3 forensic-reporting/report_generator.py --case-id CASE-0001
python3 forensic-reporting/pdf_report.py
python3 forensic-reporting/chain_of_custody.py
python3 forensic-reporting/evidence_packaging.py
```

Outputs land in `docs/sample-reports/`.

## Design principle: every claim is traceable

`report_generator.py` never invents a manipulation marker — every row in the markers
table is produced by thresholding an actual value returned by
`artifact-detection/image/gan_fingerprint.py`. When the optional `--llm` flag is used,
the LLM only *narrates* those same structured findings in plain English; it cannot add
new markers. See `docs/llm-usage-guide.md` for the full human-in-the-loop policy.
