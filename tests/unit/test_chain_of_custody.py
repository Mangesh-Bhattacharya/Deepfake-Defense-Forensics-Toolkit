import os
import tempfile
from chain_of_custody import ChainOfCustodyLog, sha256_of_bytes


def test_custody_chain_valid_after_normal_appends():
    with tempfile.TemporaryDirectory() as d:
        log = ChainOfCustodyLog(os.path.join(d, "log.jsonl"))
        log.add_entry("tester", "INGEST", "ev-1", sha256_of_bytes(b"data"), "note1")
        log.add_entry("tester", "ANALYZE", "ev-1", sha256_of_bytes(b"data"), "note2")
        assert log.verify_chain() is True
        assert len(log.read_all()) == 2


def test_custody_chain_detects_tampering():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "log.jsonl")
        log = ChainOfCustodyLog(path)
        log.add_entry("tester", "INGEST", "ev-1", sha256_of_bytes(b"data"), "note1")
        log.add_entry("tester", "ANALYZE", "ev-1", sha256_of_bytes(b"data"), "note2")

        # tamper with the file directly
        with open(path) as f:
            lines = f.readlines()
        import json
        tampered = json.loads(lines[0])
        tampered["notes"] = "TAMPERED"
        lines[0] = json.dumps(tampered) + "\n"
        with open(path, "w") as f:
            f.writelines(lines)

        tampered_log = ChainOfCustodyLog(path)
        assert tampered_log.verify_chain() is False
