# Deepfake Defense & Forensics Toolkit

A hands-on portfolio project demonstrating the core workflow of a **Deepfake Defense &
Digital Forensics Analyst**: detecting synthetic media, stress-testing biometric systems,
producing defensible forensic reports, evaluating AI safety guardrails, and using LLMs
responsibly to accelerate (never replace) analyst judgment.

Built to mirror the responsibilities in TELUS Digital AI Community's *Deepfake Defense &
Digital Forensics Analyst – Intermediate* role. See
[`docs/deepfake-analyst-capability-demonstration.md`](docs/deepfake-analyst-capability-demonstration.md)
for a direct responsibility → code mapping.

> **Scope note:** every script in this repo runs on CPU, with zero external datasets or
> API keys required. See "What's real vs. simulated" below.

---

## Architecture

```
                         ┌─────────────────────────────┐
                         │   datasets/generators/       │
                         │   synthetic_data_generator.py│   (local, no external data)
                         └──────────────┬───────────────┘
                                        │ real vs synthetic images
                                        ▼
┌───────────────────────────────────────────────────────────────────────────┐
│  A. artifact-detection/            B. biometric-stress-tests/              │
│  image / video / audio fingerprint  face / voice / liveness attack battery │
│  + synthetic_classifier.py          + stress_test_dashboard.py             │
└───────────────────┬───────────────────────────────┬───────────────────────┘
                     │ fingerprints, scores           │ vulnerability scores
                     ▼                                ▼
        ┌─────────────────────────┐      ┌─────────────────────────────┐
        │ D. ai-safety-evaluation/ │◄────►│ E. annotation-simulator/     │
        │ threshold tuning, drift, │      │ multi-annotator agreement,   │
        │ robustness, shield tests │      │ qualification exam, labeling │
        └────────────┬─────────────┘      └───────────────────────────────┘
                     │ calibrated thresholds + findings
                     ▼
        ┌───────────────────────────────────────────┐
        │  C. forensic-reporting/                     │
        │  Markdown / PDF report, chain-of-custody,   │
        │  evidence packaging                          │
        └──────────────────┬────────────────────────┘
                            │ structured evidence only
                            ▼
        ┌───────────────────────────────────────────┐
        │  F. llm-layer/  llm_interface.py             │
        │  Ollama (local) / Cloud (opt-in) / Mock      │
        │  narrates, explains, suggests — never decides│
        └───────────────────────────────────────────┘
```

The LLM layer sits **downstream** of every decision-making component. It never computes a
verdict, a classifier score, or a vulnerability score — those are always deterministic. It
only narrates and explains structured evidence that already exists. See
[`docs/llm-usage-guide.md`](docs/llm-usage-guide.md).

---

## Modules

| | Module | Responsibility |
|---|---|---|
| A | [`artifact-detection/`](artifact-detection/) | Video/audio/image synthetic-artifact detection + classifier |
| B | [`biometric-stress-tests/`](biometric-stress-tests/) | Face/voice spoofing + liveness bypass attack battery |
| C | [`forensic-reporting/`](forensic-reporting/) | Manipulation-marker reports, chain-of-custody, evidence packaging |
| D | [`ai-safety-evaluation/`](ai-safety-evaluation/) | Threshold calibration, robustness, evasion, drift detection |
| E | [`annotation-simulator/`](annotation-simulator/) | Multi-annotator agreement, labeling UI, qualification exam, language eval |
| F | [`llm-layer/`](llm-layer/) | Ollama/Cloud/Mock LLM abstraction + task-specific prompts |

Each module folder has its own README with a runnable quickstart.

---

## Installation

```bash
git clone https://github.com/<your-username>/Deepfake-Defense-Forensics-Toolkit.git
cd Deepfake-Defense-Forensics-Toolkit
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Optional, for real (non-mock) LLM output: install [Ollama](https://ollama.com) and see
[`llm-layer/ollama_config.md`](llm-layer/ollama_config.md).

## Quickstart (end-to-end, ~2 minutes)

```bash
# 1. Generate a local synthetic dataset
python3 datasets/generators/synthetic_data_generator.py --out datasets/synthetic_media --n 150

# 2. Train the synthetic-media classifier
python3 artifact-detection/classifier/synthetic_classifier.py

# 3. Run the biometric stress-test battery -> docs/stress_test_dashboard.html
python3 biometric-stress-tests/stress_test_dashboard.py

# 4. Generate a forensic report (add --llm for an LLM-assisted narrative)
python3 forensic-reporting/report_generator.py --case-id CASE-0001 --llm

# 5. Evaluate AI-safety guardrails
python3 ai-safety-evaluation/guardrail_scoring.py
python3 ai-safety-evaluation/model_robustness_evaluator.py
python3 ai-safety-evaluation/model_drift_detection.py

# 6. Simulate the annotation/evaluation workflow
python3 annotation-simulator/annotation_workflow_simulator.py

# 7. Run the test suite
pytest tests/ -q
```

## Example output

**Forensic report** (template-only): [`docs/sample-reports/CASE-0001_forensic_report.md`](docs/sample-reports/CASE-0001_forensic_report.md)
**Forensic report** (LLM-assisted): [`docs/sample-reports/CASE-LLM-DEMO_forensic_report.md`](docs/sample-reports/CASE-LLM-DEMO_forensic_report.md)
**PDF report**: [`docs/sample-reports/CASE-DEMO_forensic_report.pdf`](docs/sample-reports/CASE-DEMO_forensic_report.pdf)
**Biometric stress-test dashboard**: [`docs/stress_test_dashboard.html`](docs/stress_test_dashboard.html)
**Offline labeling interface**: [`docs/labeling_interface_demo.html`](docs/labeling_interface_demo.html)

## What's real vs. simulated (read this before judging accuracy numbers)

- **Real**: every algorithm executes; every reported number (accuracy, ROC-AUC, PSI,
  vulnerability score, Fleiss' Kappa) is computed from actual data at run time — nothing is
  hard-coded.
- **Simulated by design**: the dataset is procedurally generated (no GPU/scraped-data
  needed), and biometric embeddings use lightweight CPU-friendly stand-ins (HOG for faces,
  a small band-energy vector for voice) rather than a licensed ArcFace/FaceNet/d-vector
  model. Every stand-in has a documented `# SWAP-IN POINT` for the production-grade
  component. See [`docs/deepfake-analyst-capability-demonstration.md`](docs/deepfake-analyst-capability-demonstration.md#what-is-real-vs-explicitly-simulated-and-why).

## Alignment with TELUS Digital AI Community's mission

This project is structured around the same loop the AI Community runs at scale: generate/
collect data → detect → stress-test → report → evaluate/guardrail → feed learnings back
into the next model iteration — with a qualification-gated, multi-annotator, multi-language
evaluation layer (`annotation-simulator/`) reflecting the community's global, distributed
review model. The LLM layer is deliberately kept subordinate to deterministic detection
logic and human review, in line with responsible-AI practices for safety-critical content
moderation: LLMs accelerate documentation and triage, they do not make the call.

## Responsible LLM use, in one paragraph

Every LLM call in this repo takes already-computed structured evidence as input and is
scoped to narrate/explain/suggest — never to decide. Every LLM-authored report section is
visibly labeled and paired with the raw findings it was derived from. No LLM output gates
an ALLOW/BLOCK decision or a forensic verdict anywhere in this codebase. Full policy:
[`docs/llm-usage-guide.md`](docs/llm-usage-guide.md).

## Repository structure

```
Deepfake-Defense-Forensics-Toolkit/
├── artifact-detection/       # A
├── biometric-stress-tests/   # B
├── forensic-reporting/       # C
├── ai-safety-evaluation/     # D
├── annotation-simulator/     # E
├── llm-layer/                # F
│   ├── llm_interface.py
│   ├── ollama_config.md
│   └── prompts/
├── datasets/
│   ├── generators/
│   └── synthetic_media/
├── models/
├── docs/
├── tests/
│   ├── unit/
│   └── integration/
├── .github/
│   ├── workflows/
│   ├── ISSUE_TEMPLATE/
│   └── PULL_REQUEST_TEMPLATE/
├── LICENSE
├── SECURITY.md
├── CONTRIBUTING.md
└── CODE_OF_CONDUCT.md
```

## License

MIT — see [`LICENSE`](LICENSE).

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Security issues: see [`SECURITY.md`](SECURITY.md).
