# Module E — Community-Ready Evaluation Pipelines

Maps to job responsibility: *"Participate in the TELUS Digital AI Community annotation
and evaluation workflow, including qualification and native-language proficiency
requirements."*

| File | What it does |
|---|---|
| `annotation_workflow_simulator.py` | Simulates multi-annotator labeling of the synthetic dataset, computes Fleiss' Kappa inter-annotator agreement, and adjudicates via majority vote. |
| `generate_labeling_interface.py` | Builds a self-contained offline HTML labeling UI (embedded images, keyboard shortcuts, JSON export — no server, no network). |
| `qualification_exam_simulator.py` | Domain-knowledge qualification exam bank + pass/fail scoring, mirroring AI Community qualification gates. |
| `native_language_evaluation_module.py` | Demonstrates the harness structure for language-tagged annotation tasks with a lightweight language-ID cross-check and fluency-mismatch flagging. |

## Run it

```bash
python3 annotation-simulator/annotation_workflow_simulator.py
python3 annotation-simulator/generate_labeling_interface.py   # then open docs/labeling_interface_demo.html
python3 annotation-simulator/qualification_exam_simulator.py
python3 annotation-simulator/native_language_evaluation_module.py
```
