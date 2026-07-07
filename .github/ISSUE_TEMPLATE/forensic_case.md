---
name: Forensic case report issue
about: A problem with a generated forensic report, chain-of-custody log, or evidence bundle
title: "[FORENSIC CASE] "
labels: forensic-reporting
assignees: ''
---

**Case ID**

**What's wrong with the report/bundle?**
(e.g. incorrect marker threshold, broken chain-of-custody hash, malformed PDF)

**Command used to generate it**
```bash
python3 forensic-reporting/report_generator.py --case-id ...
```

**Attach or paste the relevant report/log excerpt**

**Does `ChainOfCustodyLog.verify_chain()` still return True for this case?**
