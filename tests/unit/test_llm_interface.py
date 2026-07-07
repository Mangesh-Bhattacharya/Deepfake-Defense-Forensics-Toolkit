"""Tests for the LLM abstraction layer using the offline MockClient — no
network access, no Ollama server required, deterministic."""
from llm_interface import MockClient, get_default_client


def test_mock_client_complete_returns_labeled_string():
    client = MockClient()
    out = client.complete("system", "user")
    assert "MOCK-LLM OUTPUT" in out


def test_draft_forensic_narrative_includes_case_data_context():
    client = MockClient()
    case = {"overall_verdict": "LIKELY_SYNTHETIC", "overall_confidence": 0.8,
            "evidence_description": "test evidence"}
    out = client.draft_forensic_narrative(case, [])
    assert isinstance(out, str) and len(out) > 0


def test_get_default_client_falls_back_to_mock_without_ollama(monkeypatch):
    import llm_interface as li
    monkeypatch.setattr(li, "_ollama_reachable", lambda *a, **kw: False)
    client = get_default_client()
    assert client.backend_name == "mock"


def test_annotation_helper_runs():
    client = MockClient()
    out = client.annotation_helper("a still frame from a video call", {"high_freq_energy_ratio": 0.09})
    assert isinstance(out, str) and len(out) > 0
