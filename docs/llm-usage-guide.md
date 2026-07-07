# LLM Usage Guide

## Purpose

This toolkit uses LLMs to **augment**, not replace, deterministic detection/forensics
logic. Every LLM call is scoped to one of five tasks:

1. Draft a plain-English forensic narrative from structured findings.
2. Explain a fingerprint feature vector to a non-technical stakeholder.
3. Suggest candidate detection-rule refinements from false-negative examples.
4. Help an annotator triage an ambiguous labeling case.
5. Generate new adversarial stress-test scenario ideas.
6. (Optional, vision) Comment on visible anomalies in an image/frame.

## Models used

| Model | Where | Used for |
|---|---|---|
| `llama3` (Ollama, local) | `llm-layer/llm_interface.py` `OllamaClient`, default text model | Narrative drafting, rule suggestions, annotation help, scenario generation |
| `mistral` (Ollama, local, optional) | same, via `OLLAMA_TEXT_MODEL=mistral` | Faster alternative for short structured judgments |
| `llava` (Ollama, local, optional) | `vision_comment_on_image()` | Visual anomaly commentary |
| Cloud LLM (opt-in, off by default) | `CloudClient` | Only if a team explicitly reviews data-handling and enables it |

See `llm-layer/ollama_config.md` for setup.

## How LLMs are invoked

Every high-level helper in `LLMClient` (see `llm-layer/llm_interface.py`) follows the
same pattern:

```
structured_evidence (dict/list, already computed by a detector)
        │
        ▼
  system_prompt (fixed, in llm-layer/prompts/*.txt — defines the task + guardrails)
        │
        ▼
  user_prompt (evidence serialized as JSON, embedded in the instruction)
        │
        ▼
  LLMClient.complete(system_prompt, user_prompt) -> plain text
```

The LLM never receives raw, unlabeled media and is never asked to "decide" a verdict —
verdicts and manipulation markers always come from `artifact-detection/`,
`biometric-stress-tests/`, or `ai-safety-evaluation/`. The LLM's job is strictly
narration, explanation, and suggestion.

## Prompt design

All system prompts live in `llm-layer/prompts/` as plain text files (not embedded in
Python) so they can be reviewed, versioned, and audited independently of code. Each one
explicitly instructs the model to:
- work only from the structured data provided,
- avoid inventing new findings,
- and (where relevant) state that its output is a draft requiring human review.

## Limitations

- **No LLM output gates a real decision.** Content-safety ALLOW/REVIEW/BLOCK decisions
  (`ai-safety-evaluation/synthetic_media_shield_harness.py`) and forensic verdicts
  (`forensic-reporting/report_generator.py`) are computed entirely from classifier scores
  and rule thresholds. LLM narrative text is additive and clearly labeled.
- **The offline `MockClient` is not a real model.** When no Ollama server is reachable,
  every LLM-assisted script still runs (so the repo is fully demonstrable/testable
  without any LLM installed) but returns a clearly-marked template string, not generated
  text. Install Ollama (see `llm-layer/ollama_config.md`) to see real model output.
- **Hallucination risk.** Even with a real backend, LLM narrative sections should be spot
  checked against the structured markers table before a report is finalized — this is why
  every report includes both the raw findings table and the narrative, side by side.
- **Vision commentary is supplementary.** `llava`-based image commentary is one more
  input for a human analyst to weigh, not a standalone detector.

## Human-in-the-loop policy

1. LLM-authored sections are always visually distinguished (blockquote + explicit label)
   in generated reports.
2. `forensic-reporting/report_generator.py` requires the `--llm` flag to opt in; the
   default is template-only, zero-LLM report generation.
3. A human analyst must review and countersign any LLM-assisted report before it is used
   in a legal, HR, or compliance context (see the disclaimer on every generated report).
