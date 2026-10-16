# -*- coding: utf-8 -*-
"""Merge translation batches, report coverage and conflicts."""
import sys, io, json
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
BASE = Path(r"C:\Users\fanchengpeng\.zcode\workspace\default\rogue-tower-cn")

merged = {}
conflicts = []
for f in sorted((BASE / "trans").glob("batch_*.json")):
    data = json.loads(f.read_text(encoding="utf-8"))
    for k, v in data.items():
        if k in merged and merged[k] != v:
            conflicts.append((k, merged[k], v, f.name))
        merged[k] = v

keys = (BASE / "final_keys.txt").read_text(encoding="utf-8").splitlines()
covered = [k for k in keys if k in merged]
missing = [k for k in keys if k not in merged]
extra = [k for k in merged if k not in set(keys)]

(BASE / "translations.json").write_text(json.dumps(merged, ensure_ascii=False, indent=1), encoding="utf-8")

print(f"translated entries: {len(merged)}")
print(f"final keys: {len(keys)}  covered: {len(covered)}  missing: {len(missing)}")
print(f"extra (not in final list): {len(extra)}")
print(f"conflicts: {len(conflicts)}")
for c in conflicts[:10]:
    print("  CONFLICT:", c[0][:50], "|", c[1][:30], "|", c[2][:30], "|", c[3])
print("--- missing keys ---")
for m in missing:
    print(repr(m))
print("--- extra keys ---")
for e in extra[:20]:
    print(repr(e))
