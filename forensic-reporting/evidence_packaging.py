"""
evidence_packaging.py
------------------------
Packages evidence + forensic report + chain-of-custody log into a single,
tamper-evident ZIP bundle suitable for handoff (e.g. to a case owner, legal,
or the TELUS AI Community review queue).

The bundle includes a MANIFEST.json listing every file's SHA-256 hash, so a
recipient can verify nothing was altered after packaging.
"""
from __future__ import annotations

import json
import os
import zipfile
from datetime import datetime, timezone
from typing import List

import sys
sys.path.append(os.path.dirname(__file__))
from chain_of_custody import sha256_of_file  # noqa: E402


def package_evidence(case_id: str, file_paths: List[str], out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    zip_path = os.path.join(out_dir, f"{case_id}_evidence_bundle.zip")

    manifest = {
        "case_id": case_id,
        "packaged_at": datetime.now(timezone.utc).isoformat(),
        "files": [],
    }
    for p in file_paths:
        if os.path.exists(p):
            manifest["files"].append({
                "filename": os.path.basename(p),
                "sha256": sha256_of_file(p),
                "size_bytes": os.path.getsize(p),
            })

    manifest_path = os.path.join(out_dir, f"{case_id}_MANIFEST.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in file_paths:
            if os.path.exists(p):
                zf.write(p, arcname=os.path.basename(p))
        zf.write(manifest_path, arcname=os.path.basename(manifest_path))

    return zip_path


def verify_bundle(zip_path: str) -> bool:
    """Extracts the manifest from the zip and verifies every file's hash matches."""
    with zipfile.ZipFile(zip_path) as zf:
        manifest_name = next((n for n in zf.namelist() if n.endswith("_MANIFEST.json")), None)
        if not manifest_name:
            return False
        manifest = json.loads(zf.read(manifest_name))
        for entry in manifest["files"]:
            data = zf.read(entry["filename"])
            import hashlib
            actual_hash = hashlib.sha256(data).hexdigest()
            if actual_hash != entry["sha256"]:
                return False
    return True


if __name__ == "__main__":
    demo_dir = os.path.join(os.path.dirname(__file__), "..", "docs", "sample-reports")
    files = [
        os.path.join(demo_dir, "CASE-0001_forensic_report.md"),
        os.path.join(demo_dir, "CASE-0001_forensic_report.json"),
    ]
    files = [f for f in files if os.path.exists(f)]
    if files:
        bundle = package_evidence("CASE-0001", files, demo_dir)
        print(f"Bundle written: {bundle}")
        print(f"Bundle integrity verified: {verify_bundle(bundle)}")
    else:
        print("Run report_generator.py first to produce evidence to package.")
