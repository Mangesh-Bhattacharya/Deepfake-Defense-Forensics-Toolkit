"""
llm_interface.py
-------------------
LLM abstraction layer for the Deepfake Defense & Forensics Toolkit.

Provides one interface (`LLMClient`) with three interchangeable backends:

  * OllamaClient  - talks to a local Ollama server (http://localhost:11434) running
                    a model such as `llama3`, `mistral`, or the vision model `llava`.
                    This is the RECOMMENDED backend for this toolkit: fully local,
                    no data leaves the machine, appropriate for handling sensitive
                    forensic evidence.
  * CloudClient   - thin wrapper for a cloud LLM API (e.g. Anthropic/OpenAI). Reads
                    its API key from an environment variable and is OFF by default.
                    Provided for teams that explicitly choose cloud inference after
                    a data-handling review (see docs/llm-usage-guide.md).
  * MockClient    - deterministic, offline, zero-dependency backend used as the
                    default fallback so every script in this repo (report drafting,
                    annotation help, scenario generation, ...) runs end-to-end even
                    with no LLM installed. It returns clearly-labeled template text,
                    NEVER fabricated "AI-sounding" claims dressed up as real output.

get_default_client() auto-selects: Ollama if reachable -> else Mock (never silently
falls back to a cloud call). Callers can also construct a specific backend directly.

RESPONSIBLE-USE CONTRACT (enforced structurally, not just by prompt wording):
  1. Every LLM call in this repo takes STRUCTURED, already-computed evidence as
     input (fingerprint dicts, classifier scores, custody metadata) — the LLM is
     asked to narrate/explain/suggest, never to invent detection results.
  2. Every LLM-authored section of a report is explicitly labeled as LLM-assisted
     and paired with the underlying structured data so a human can verify it.
  3. No LLM output is used to auto-approve/auto-block real content in any module —
     ai-safety-evaluation/ and forensic-reporting/ gate decisions on the classifier
     + rule thresholds, never on LLM free text.
"""
from __future__ import annotations

import json
import os
import socket
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from typing import Dict, List


OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_TEXT_MODEL = os.environ.get("OLLAMA_TEXT_MODEL", "llama3")
OLLAMA_VISION_MODEL = os.environ.get("OLLAMA_VISION_MODEL", "llava")


class LLMClient(ABC):
    """Common interface every backend implements."""

    backend_name: str = "abstract"

    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Return a single text completion for the given prompt pair."""

    # ---- High-level, task-specific helpers (built on top of `complete`) ----

    def draft_forensic_narrative(self, case: Dict, markers: List[Dict]) -> str:
        system = load_prompt("forensic_report_narrative_system.txt")
        user = (
            f"Case verdict: {case.get('overall_verdict')}\n"
            f"Confidence: {case.get('overall_confidence')}\n"
            f"Evidence description: {case.get('evidence_description')}\n"
            f"Structured markers (do not add markers beyond this list): "
            f"{json.dumps(markers, indent=2)}\n\n"
            "Write a 2-3 paragraph plain-English narrative summary for a non-technical "
            "stakeholder, based ONLY on the structured data above."
        )
        return self.complete(system, user)

    def explain_artifact_for_stakeholder(self, fingerprint: Dict[str, float]) -> str:
        system = load_prompt("artifact_explanation_system.txt")
        user = (
            f"Fingerprint feature values:\n{json.dumps(fingerprint, indent=2)}\n\n"
            "Explain what these values suggest, in plain English, for someone unfamiliar with signal processing."
        )
        return self.complete(system, user)

    def suggest_detection_rules(self, false_negative_examples: List[Dict]) -> str:
        system = load_prompt("rule_suggestion_system.txt")
        user = (
            f"These synthetic samples were MISSED by the current classifier (false negatives):\n"
            f"{json.dumps(false_negative_examples, indent=2)}\n\n"
            "Suggest 2-4 candidate detection-rule or feature refinements a human engineer should evaluate."
        )
        return self.complete(system, user)

    def annotation_helper(self, sample_description: str, fingerprint: Dict[str, float]) -> str:
        system = load_prompt("annotation_helper_system.txt")
        user = (
            f"Sample description: {sample_description}\nFingerprint: {json.dumps(fingerprint, indent=2)}\n\n"
            "Propose a label (real/synthetic/uncertain), a confidence 0-1, and flag if this case looks ambiguous and why."
        )
        return self.complete(system, user)

    def generate_stress_test_scenario(self, system_type: str) -> str:
        system = load_prompt("scenario_generator_system.txt")
        user = (
            f"Propose one new adversarial stress-test scenario for a '{system_type}' biometric/safety system "
            "that is NOT already in this toolkit's attack battery. Describe the attack vector and what signal "
            "would reveal it."
        )
        return self.complete(system, user)

    def vision_comment_on_image(self, image_description_or_path: str) -> str:
        system = load_prompt("vision_commentary_system.txt")
        user = (
            f"Image reference: {image_description_or_path}\n\n"
            "Describe any visible anomalies consistent with synthetic-media generation (only describe what a "
            "vision-capable model would plausibly observe; this mock backend cannot see the image)."
        )
        return self.complete(system, user)


def load_prompt(filename: str) -> str:
    path = os.path.join(os.path.dirname(__file__), "prompts", filename)
    with open(path) as f:
        return f.read()


class MockClient(LLMClient):
    """Deterministic, offline backend. Default fallback so this repo runs
    end-to-end with zero external services. Clearly labels its own output as
    a template/mock so nobody mistakes it for a real model's reasoning."""

    backend_name = "mock"

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        return (
            "[MOCK-LLM OUTPUT — no local Ollama server or cloud API was reachable; "
            "install & run Ollama (see llm-layer/ollama_config.md) for real generative output]\n\n"
            f"Based on the structured evidence provided, this would normally be narrated by "
            f"'{OLLAMA_TEXT_MODEL}'. Summary of inputs the model was given:\n"
            f"{_truncate(user_prompt, 600)}"
        )


class OllamaClient(LLMClient):
    """Talks to a local Ollama server. Requires `ollama serve` running and the
    target model pulled (`ollama pull llama3`)."""

    backend_name = "ollama"

    def __init__(self, host: str = OLLAMA_HOST, model: str = OLLAMA_TEXT_MODEL, timeout: float = 30.0):
        self.host = host
        self.model = model
        self.timeout = timeout

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        payload = json.dumps({
            "model": self.model,
            "prompt": f"{system_prompt}\n\n{user_prompt}",
            "stream": False,
        }).encode()
        req = urllib.request.Request(
            f"{self.host}/api/generate", data=payload,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        # nosec B310 -- host is OLLAMA_HOST, an operator-configured local endpoint,
        # not user-controlled input; restrict this to trusted hosts only.
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # nosec B310
            body = json.loads(resp.read())
        return body.get("response", "").strip()


class CloudClient(LLMClient):
    """Thin, OFF-BY-DEFAULT wrapper for a cloud LLM API. Reads the API key from
    an environment variable and never activates implicitly — a caller must
    explicitly instantiate this class. See docs/llm-usage-guide.md for the
    data-handling review this requires before use on real evidence."""

    backend_name = "cloud"

    def __init__(self, api_key_env: str = "CLOUD_LLM_API_KEY", model: str = "claude-sonnet-5"):
        self.api_key = os.environ.get(api_key_env)
        self.model = model
        if not self.api_key:
            raise RuntimeError(
                f"CloudClient requires the {api_key_env} environment variable. "
                "Cloud inference is opt-in only — see docs/llm-usage-guide.md."
            )

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError(
            "Wire this method to your chosen cloud provider's SDK. Left unimplemented "
            "intentionally so this toolkit never makes an accidental network call with "
            "sensitive forensic evidence — see docs/llm-usage-guide.md 'cloud opt-in policy'."
        )


def _ollama_reachable(host: str = OLLAMA_HOST, timeout: float = 0.5) -> bool:
    try:
        from urllib.parse import urlparse
        parsed = urlparse(host)
        with socket.create_connection((parsed.hostname, parsed.port or 80), timeout=timeout):
            return True
    except OSError:
        return False


def get_default_client() -> LLMClient:
    """Ollama if reachable, else the offline Mock backend. Never auto-selects
    CloudClient — cloud inference must be requested explicitly."""
    if _ollama_reachable():
        return OllamaClient()
    return MockClient()


def _truncate(text: str, n: int) -> str:
    return text if len(text) <= n else text[:n] + "... [truncated]"


if __name__ == "__main__":
    client = get_default_client()
    print(f"Using backend: {client.backend_name}")
    demo_case = {
        "overall_verdict": "LIKELY_SYNTHETIC", "overall_confidence": 0.93,
        "evidence_description": "Demo image analyzed for synthetic-media artifacts.",
    }
    demo_markers = [{
        "marker_type": "checkerboard_score", "confidence": 0.81,
        "detail": "Checkerboard-pattern response consistent with GAN upsampling.",
    }]
    print(client.draft_forensic_narrative(demo_case, demo_markers))
