# Contributing

Thanks for considering a contribution to the Deepfake Defense & Forensics Toolkit.

## Development setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
```

## Before opening a PR

```bash
flake8 . --max-line-length=160 --exclude=.venv,datasets/synthetic_media
bandit -r . -x ./tests,./.venv
pytest tests/ -q --cov=.
```

All three must pass (see `.github/workflows/ci.yml` — the same commands run in CI).

## Guidelines

- **No real biometric/deepfake data in PRs.** This repo intentionally uses only
  procedurally generated synthetic data (`datasets/generators/`). Do not add scraped faces,
  voices, or third-party deepfake corpora — open an issue first if you think real data is
  necessary for a specific improvement.
- **Every detector claim must be verifiable.** If you add a new detection feature or
  metric, include the code that computes it and a test that exercises it — no hard-coded
  "accuracy" numbers in docs.
- **LLM changes**: new prompts go in `llm-layer/prompts/` as plain text, not inline in
  Python. Read `docs/llm-usage-guide.md` before changing anything in `llm-layer/`.
- **New modules**: add a module-level `README.md` following the pattern in the existing
  six modules (table of files, quickstart commands).

## Commit style

Conventional-commit-ish prefixes are appreciated but not enforced: `feat:`, `fix:`,
`docs:`, `test:`, `refactor:`.
