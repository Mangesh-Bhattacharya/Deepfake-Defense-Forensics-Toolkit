## Summary

<!-- What does this PR change and why? -->

## Module(s) touched

- [ ] artifact-detection
- [ ] biometric-stress-tests
- [ ] forensic-reporting
- [ ] ai-safety-evaluation
- [ ] annotation-simulator
- [ ] llm-layer
- [ ] docs / CI / other

## Checklist

- [ ] `flake8 . --max-line-length=160` passes
- [ ] `bandit -r . -x ./tests,./.venv` passes
- [ ] `pytest tests/ -q` passes
- [ ] No real/scraped biometric or deepfake data added — only locally generated synthetic data
- [ ] New/changed detector or metric is backed by a test, not just a docstring claim
- [ ] If `llm-layer/` changed: prompts still live in `llm-layer/prompts/*.txt`, not inline in Python
- [ ] Relevant module README updated

## How was this tested?

<!-- Commands run + output, or link to CI run -->
