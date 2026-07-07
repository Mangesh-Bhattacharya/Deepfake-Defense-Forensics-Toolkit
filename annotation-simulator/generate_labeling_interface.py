"""
generate_labeling_interface.py
------------------------------------
Generates a single self-contained HTML labeling interface for the synthetic
media dataset — a lightweight stand-in for the kind of annotation UI used in
AI Community labeling queues. Images are embedded as base64 so the resulting
HTML file works completely offline with no server.

Annotators click Real / Synthetic / Uncertain for each sample; keyboard
shortcuts (R / S / U) are supported. Labels are held in-browser and can be
exported as JSON via the "Export labels" button (downloads a .json file —
no network calls, no external storage).
"""
from __future__ import annotations

import base64
import json
import os
import sys


def build_html(data_dir: str, out_path: str, max_samples: int = 24) -> str:
    manifest_path = os.path.join(data_dir, "manifest.json")
    with open(manifest_path) as f:
        manifest = json.load(f)[:max_samples]

    cards = []
    for rec in manifest:
        img_path = os.path.join(data_dir, rec["filename"])
        with open(img_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        cards.append({"filename": rec["filename"], "b64": b64})

    cards_json = json.dumps(cards)

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Synthetic Media Labeling Interface</title>
<style>
body {{ font-family: -apple-system, Arial, sans-serif; background:#0f1115; color:#eee; margin:0; padding:24px; }}
h1 {{ font-size:1.4em; }}
.toolbar {{ margin-bottom:16px; }}
button.export {{ background:#2c7be5; color:#fff; border:none; padding:8px 14px; border-radius:6px; cursor:pointer; }}
.grid {{ display:grid; grid-template-columns: repeat(auto-fill, minmax(180px,1fr)); gap:16px; }}
.card {{ background:#1b1e26; border-radius:8px; padding:10px; text-align:center; }}
.card img {{ width:100%; image-rendering:pixelated; border-radius:4px; }}
.label-row button {{ margin:4px 2px; padding:6px 8px; border-radius:4px; border:1px solid #444; cursor:pointer; background:#2a2e38; color:#eee; }}
.label-row button.active-real {{ background:#27ae60; }}
.label-row button.active-synthetic {{ background:#c0392b; }}
.label-row button.active-uncertain {{ background:#e67e22; }}
.progress {{ margin:10px 0; color:#aaa; font-size:0.9em; }}
</style></head>
<body>
<h1>Synthetic Media Labeling Interface (offline demo)</h1>
<div class="toolbar">
  <button class="export" onclick="exportLabels()">Export labels (.json)</button>
  <span class="progress" id="progress"></span>
</div>
<div class="grid" id="grid"></div>

<script>
const cards = {cards_json};
const labels = {{}};

function render() {{
  const grid = document.getElementById('grid');
  grid.innerHTML = '';
  cards.forEach(c => {{
    const div = document.createElement('div');
    div.className = 'card';
    const label = labels[c.filename] || null;
    div.innerHTML = `
      <img src="data:image/png;base64,${{c.b64}}" />
      <div style="font-size:0.75em;color:#888;margin-top:4px">${{c.filename}}</div>
      <div class="label-row">
        <button class="${{label==='real'?'active-real':''}}" onclick="setLabel('${{c.filename}}','real')">Real (R)</button>
        <button class="${{label==='synthetic'?'active-synthetic':''}}" onclick="setLabel('${{c.filename}}','synthetic')">Synthetic (S)</button>
        <button class="${{label==='uncertain'?'active-uncertain':''}}" onclick="setLabel('${{c.filename}}','uncertain')">Uncertain (U)</button>
      </div>`;
    grid.appendChild(div);
  }});
  updateProgress();
}}

function setLabel(filename, label) {{
  labels[filename] = label;
  render();
}}

function updateProgress() {{
  const done = Object.keys(labels).length;
  document.getElementById('progress').innerText = `${{done}} / ${{cards.length}} labeled`;
}}

function exportLabels() {{
  const blob = new Blob([JSON.stringify(labels, null, 2)], {{type: 'application/json'}});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'annotation_labels.json';
  a.click();
}}

render();
</script>
</body></html>"""

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w") as f:
        f.write(html)
    return out_path


if __name__ == "__main__":
    data_dir = os.path.join(os.path.dirname(__file__), "..", "datasets", "synthetic_media")
    out_path = os.path.join(os.path.dirname(__file__), "..", "docs", "labeling_interface_demo.html")
    if not os.path.exists(os.path.join(data_dir, "manifest.json")):
        print("Generate the dataset first: python3 datasets/generators/synthetic_data_generator.py")
        sys.exit(0)
    path = build_html(data_dir, out_path)
    print(f"Labeling interface written to {path}")
