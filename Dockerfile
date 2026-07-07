# Dockerfile -- containerized environment for the Deepfake Defense & Forensics Toolkit.
#
# Builds a slim, CPU-only image with Python + Node.js so both
# artifact-detection/forensic-reporting (Python) and the evidence bundle
# verifier (tools/node-evidence-verifier, Node.js) work out of the box.
#
# Build:  docker build -t deepfake-defense-forensics-toolkit .
# Run:    docker run --rm deepfake-defense-forensics-toolkit
#         (runs scripts/run_full_demo.sh by default -- see CMD below)

FROM python:3.11-slim AS base

# System deps: Node.js (for tools/node-evidence-verifier) + build tools OpenCV
# needs at import time (libgl1, libglib2.0-0), kept minimal for image size.
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        libgl1 \
        libglib2.0-0 \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY . .
RUN chmod +x scripts/*.sh tools/node-evidence-verifier/verify_bundle.js

# Non-root user -- this toolkit may handle sensitive forensic evidence in
# real deployments; don't run as root by default.
RUN useradd --create-home --shell /bin/bash toolkit \
    && chown -R toolkit:toolkit /app
USER toolkit

CMD ["./scripts/run_full_demo.sh"]
