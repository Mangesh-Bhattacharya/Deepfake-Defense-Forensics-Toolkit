# Security Policy

## Scope

This is a research/portfolio toolkit for synthetic-media detection and digital forensics
education. It does not process real user biometric data by default (all demo data is
procedurally generated locally).

## Reporting a Vulnerability

If you find a security issue (e.g. a path traversal in `evidence_packaging.py`, an
injection risk in report rendering, or an unsafe deserialization path), please:

1. **Do not** open a public GitHub issue with exploit details.
2. Email the maintainer (see repository owner profile) with a description, reproduction
   steps, and potential impact.
3. Allow a reasonable window for a fix before any public disclosure.

## Known limitations (not vulnerabilities, but worth knowing)

- `llm-layer/llm_interface.py`'s `OllamaClient` sends prompts to whatever `OLLAMA_HOST`
  points at — do not point it at an untrusted host.
- `forensic-reporting/chain_of_custody.py`'s hash chain proves *integrity*, not
  *authenticity* — it detects tampering after the fact but does not itself authenticate
  the original evidence source. Combine with your organization's evidence-intake controls.
- This toolkit is not a certified forensic tool; see the disclaimer on every generated
  report.
