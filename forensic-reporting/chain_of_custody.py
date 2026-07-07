"""
chain_of_custody.py
----------------------
Chain-of-custody logging for digital forensic evidence.

Every piece of evidence (image, video, audio, or a generated report) that
enters this toolkit's forensic workflow gets a custody record: who/what
handled it, when, what action was taken, and a SHA-256 hash to prove the
bytes were not altered between steps. Records are appended to a
tamper-evident JSON-lines log (each entry's hash chains to the previous
entry's hash, similar in spirit to a simple blockchain / git commit chain).
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import List


def sha256_of_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_of_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass
class CustodyEntry:
    timestamp: str
    actor: str
    action: str
    evidence_id: str
    evidence_hash: str
    notes: str
    prev_entry_hash: str
    entry_hash: str = ""

    def compute_entry_hash(self) -> str:
        payload = json.dumps({
            "timestamp": self.timestamp,
            "actor": self.actor,
            "action": self.action,
            "evidence_id": self.evidence_id,
            "evidence_hash": self.evidence_hash,
            "notes": self.notes,
            "prev_entry_hash": self.prev_entry_hash,
        }, sort_keys=True).encode()
        return sha256_of_bytes(payload)


class ChainOfCustodyLog:
    """Append-only, hash-chained custody log stored as JSON-lines."""

    GENESIS_HASH = "0" * 64

    def __init__(self, log_path: str):
        self.log_path = log_path
        os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
        if not os.path.exists(log_path):
            open(log_path, "w").close()

    def _last_entry_hash(self) -> str:
        entries = self.read_all()
        return entries[-1].entry_hash if entries else self.GENESIS_HASH

    def add_entry(self, actor: str, action: str, evidence_id: str, evidence_hash: str, notes: str = "") -> CustodyEntry:
        entry = CustodyEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            actor=actor,
            action=action,
            evidence_id=evidence_id,
            evidence_hash=evidence_hash,
            notes=notes,
            prev_entry_hash=self._last_entry_hash(),
        )
        entry.entry_hash = entry.compute_entry_hash()
        with open(self.log_path, "a") as f:
            f.write(json.dumps(asdict(entry)) + "\n")
        return entry

    def read_all(self) -> List[CustodyEntry]:
        entries = []
        if not os.path.exists(self.log_path):
            return entries
        with open(self.log_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(CustodyEntry(**json.loads(line)))
        return entries

    def verify_chain(self) -> bool:
        """Recomputes every entry hash and checks the chain links; returns
        False the moment any record has been tampered with or reordered."""
        entries = self.read_all()
        prev = self.GENESIS_HASH
        for e in entries:
            if e.prev_entry_hash != prev:
                return False
            recomputed = CustodyEntry(
                timestamp=e.timestamp, actor=e.actor, action=e.action,
                evidence_id=e.evidence_id, evidence_hash=e.evidence_hash,
                notes=e.notes, prev_entry_hash=e.prev_entry_hash,
            ).compute_entry_hash()
            if recomputed != e.entry_hash:
                return False
            prev = e.entry_hash
        return True


if __name__ == "__main__":
    import tempfile as _tempfile
    log = ChainOfCustodyLog(os.path.join(_tempfile.gettempdir(), "demo_custody_log.jsonl"))
    log.add_entry("analyst.mangesh", "INGEST", "evidence-001", sha256_of_bytes(b"demo bytes"), "Initial ingest of uploaded video")
    log.add_entry("pipeline.artifact_detector", "ANALYZE", "evidence-001", sha256_of_bytes(b"demo bytes"), "Ran frame_anomaly_scanner.py")
    log.add_entry("pipeline.report_generator", "REPORT", "evidence-001", sha256_of_bytes(b"demo bytes"), "Generated forensic_report.md")
    print("Chain valid:", log.verify_chain())
    for e in log.read_all():
        print(f"  {e.timestamp}  {e.actor:28s} {e.action:10s} {e.entry_hash[:12]}...")
