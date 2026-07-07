#!/usr/bin/env bash
# run_full_demo.sh -- runs the full "Suggested review path" from
# docs/deepfake-analyst-capability-demonstration.md end-to-end, in order.
#
# Intended to be the single command a reviewer (or CI) runs to see every
# module produce real, freshly-computed output. Exits non-zero on the first
# failing step (set -e).
#
# Usage:
#   ./scripts/run_full_demo.sh [--n-samples 150]

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

N_SAMPLES=150
while [[ $# -gt 0 ]]; do
  case "$1" in
    --n-samples)
      N_SAMPLES="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

step() {
  echo ""
  echo "=================================================================="
  echo "==> $1"
  echo "=================================================================="
}

step "1/8  Generating local synthetic dataset (n=${N_SAMPLES} per class)"
python3 datasets/generators/synthetic_data_generator.py --out datasets/synthetic_media --n "$N_SAMPLES"

step "2/8  Training the synthetic-media classifier"
python3 artifact-detection/classifier/synthetic_classifier.py

step "3/8  Running the biometric stress-test battery"
python3 biometric-stress-tests/stress_test_dashboard.py > /dev/null
echo "    -> docs/stress_test_dashboard.html"

step "4/8  Generating a forensic report (template + LLM-assisted)"
python3 forensic-reporting/report_generator.py --case-id CASE-DEMO-RUN
python3 forensic-reporting/report_generator.py --case-id CASE-DEMO-RUN-LLM --llm > /dev/null
python3 forensic-reporting/pdf_report.py > /dev/null
python3 forensic-reporting/evidence_packaging.py

step "5/8  Verifying the evidence bundle independently (Node.js, zero deps)"
if command -v node >/dev/null 2>&1; then
  LATEST_BUNDLE="$(ls -t docs/sample-reports/*_evidence_bundle.zip | head -1)"
  node tools/node-evidence-verifier/verify_bundle.js "$LATEST_BUNDLE"
else
  echo "    (skipped: node not found)"
fi

step "6/8  Running AI-safety guardrail evaluation"
python3 ai-safety-evaluation/guardrail_scoring.py
python3 ai-safety-evaluation/model_robustness_evaluator.py
python3 ai-safety-evaluation/synthetic_media_shield_harness.py
python3 ai-safety-evaluation/model_drift_detection.py

step "7/8  Running the annotation/evaluation workflow simulation"
python3 annotation-simulator/annotation_workflow_simulator.py
python3 annotation-simulator/qualification_exam_simulator.py
python3 annotation-simulator/native_language_evaluation_module.py

step "8/8  Running the full test suite (pytest + node --test)"
python3 -m pytest tests/ -q
if command -v node >/dev/null 2>&1; then
  node --test tools/node-evidence-verifier/test/verify_bundle.test.js
fi

echo ""
echo "All modules ran successfully end-to-end."
