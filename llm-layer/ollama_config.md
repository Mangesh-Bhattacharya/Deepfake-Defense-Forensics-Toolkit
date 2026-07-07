# Ollama Configuration

This toolkit's `llm_interface.py` is built to talk to a **local Ollama server** by
default — no data leaves your machine, which matters when the "evidence" being narrated
is real forensic material.

## 1. Install Ollama

- macOS / Windows: download from https://ollama.com
- Linux: `curl -fsSL https://ollama.com/install.sh | sh`

## 2. Pull the models this toolkit uses

```bash
ollama pull llama3     # text: forensic narrative drafting, rule suggestions, annotation help
ollama pull mistral     # optional alternative text model — set OLLAMA_TEXT_MODEL=mistral
ollama pull llava       # optional vision model — image/frame anomaly commentary
```

## 3. Start the server

```bash
ollama serve
```

By default it listens on `http://localhost:11434`.

## 4. Point the toolkit at it (usually automatic)

`llm_interface.get_default_client()` probes `http://localhost:11434` and uses
`OllamaClient` automatically if it's reachable, otherwise falls back to the offline
`MockClient`. To override:

```bash
export OLLAMA_HOST=http://localhost:11434
export OLLAMA_TEXT_MODEL=llama3
export OLLAMA_VISION_MODEL=llava
```

## 5. Verify

```bash
python3 llm-layer/llm_interface.py
# should print "Using backend: ollama" instead of "Using backend: mock"
```

## Model selection guidance

| Task | Recommended model | Why |
|---|---|---|
| Forensic narrative drafting | `llama3` | Strong instruction-following on structured-to-prose tasks |
| Rule/guardrail suggestions | `llama3` or `mistral` | Reasoning over feature/threshold data |
| Annotation triage help | `mistral` | Fast, good for short structured judgments |
| Image/frame anomaly commentary | `llava` | Only Ollama-hosted model in this list with vision input |

## Cloud opt-in (off by default)

`llm_interface.CloudClient` exists for teams that have explicitly reviewed and approved
sending (non-sensitive, already-redacted) evidence summaries to a cloud LLM API. It is
never auto-selected by `get_default_client()` — you must construct it directly and wire
`complete()` to your provider's SDK. See `docs/llm-usage-guide.md` for the data-handling
checklist to complete first.
