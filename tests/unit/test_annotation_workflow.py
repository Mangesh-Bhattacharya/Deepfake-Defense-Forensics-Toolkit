from annotation_workflow_simulator import cohens_kappa, fleiss_kappa, interpret_kappa


def test_cohens_kappa_perfect_agreement():
    labels_a = ["real", "synthetic", "real", "synthetic"]
    labels_b = ["real", "synthetic", "real", "synthetic"]
    assert cohens_kappa(labels_a, labels_b) == 1.0


def test_fleiss_kappa_perfect_agreement():
    annotations = {
        "t1": ["real", "real", "real"],
        "t2": ["synthetic", "synthetic", "synthetic"],
        "t3": ["real", "real", "real"],
    }
    assert fleiss_kappa(annotations) == 1.0


def test_interpret_kappa_labels():
    assert interpret_kappa(0.9) == "almost perfect agreement"
    assert interpret_kappa(0.1) == "slight agreement"
    assert interpret_kappa(-0.5) == "poor (worse than chance)"
