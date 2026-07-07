# Makefile -- common developer commands for the Deepfake Defense & Forensics Toolkit.
# Run `make help` to list targets.

PYTHON ?= python3
PIP ?= pip3
DATA_DIR := datasets/synthetic_media
N ?= 150

.PHONY: help setup dataset train test test-node lint security demo verify-bundle docker-build docker-run clean

help:
	@echo "Deepfake Defense & Forensics Toolkit -- make targets:"
	@echo "  make setup          Create .venv and install requirements-dev.txt"
	@echo "  make dataset        Generate the local synthetic dataset (N=$(N) per class)"
	@echo "  make train          Train the synthetic-media classifier"
	@echo "  make test           Run the Python test suite (pytest)"
	@echo "  make test-node      Run the Node.js evidence-bundle verifier tests"
	@echo "  make lint           Run flake8"
	@echo "  make security       Run bandit"
	@echo "  make demo           Run the full end-to-end demo (scripts/run_full_demo.sh)"
	@echo "  make verify-bundle  Verify the latest evidence bundle with the Node.js tool"
	@echo "  make docker-build   Build the toolkit's Docker image"
	@echo "  make docker-run     Run the full demo inside Docker"
	@echo "  make clean          Remove caches, coverage files, and __pycache__"

setup:
	./scripts/setup.sh --dev

dataset:
	$(PYTHON) datasets/generators/synthetic_data_generator.py --out $(DATA_DIR) --n $(N)

train: dataset
	$(PYTHON) artifact-detection/classifier/synthetic_classifier.py

test:
	$(PYTHON) -m pytest tests/ -q --cov=. --cov-report=term-missing

test-node:
	node --test tools/node-evidence-verifier/test/verify_bundle.test.js

lint:
	flake8 . --max-line-length=160 --exclude=.venv,datasets/synthetic_media,build,dist

security:
	bandit -r . -x ./tests,./.venv -ll

demo:
	./scripts/run_full_demo.sh --n-samples $(N)

verify-bundle:
	@LATEST=$$(ls -t docs/sample-reports/*_evidence_bundle.zip 2>/dev/null | head -1); \
	if [ -z "$$LATEST" ]; then \
		echo "No evidence bundle found -- run 'make demo' first."; exit 1; \
	fi; \
	node tools/node-evidence-verifier/verify_bundle.js "$$LATEST"

docker-build:
	docker build -t deepfake-defense-forensics-toolkit .

docker-run:
	docker run --rm deepfake-defense-forensics-toolkit

clean:
	find . -type d -name "__pycache__" -not -path "./.venv/*" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .coverage htmlcov
