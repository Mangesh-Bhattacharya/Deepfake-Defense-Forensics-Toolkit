"""Integration test for the biometric stress-test dashboard aggregation."""
from stress_test_dashboard import run_all_stress_tests


def test_dashboard_aggregates_all_three_subsystems():
    report = run_all_stress_tests(seed=2)
    names = {s.subsystem for s in report.subsystems}
    assert names == {"face_recognition", "voice_recognition", "liveness_detection"}
    assert 0.0 <= report.overall_vulnerability_score <= 1.0
    for s in report.subsystems:
        assert s.total_attacks > 0
