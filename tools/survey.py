# -*- coding: utf-8 -*-
"""Survey Rogue Tower assets: object types, script names, text fields, fonts."""
import sys, io, json, collections
from pathlib import Path
import UnityPy

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

GAME = Path(r"D:\Steam\steamapps\common\Rogue Tower\Rogue Tower_Data")
FILES = ["level0", "level1", "sharedassets0.assets", "sharedassets1.assets",
         "globalgamemanagers.assets", "globalgamemanagers"]

for fname in FILES:
    p = GAME / fname
    if not p.exists():
        continue
    try:
        env = UnityPy.load(str(p))
    except Exception as e:
        print(f"{fname}: LOAD FAILED {e}")
        continue
    types = collections.Counter()
    scripts = collections.Counter()
    for obj in env.objects:
        types[obj.type.name] += 1
        if obj.type.name == "MonoBehaviour":
            try:
                d = obj.read(check_read=False)
                script = getattr(d, "m_Script", None)
                if script:
                    scripts[script.read().m_ClassName] += 1
            except Exception:
                scripts["<unreadable>"] += 1
    print(f"=== {fname}")
    print("  types:", dict(types.most_common()))
    if scripts:
        print("  scripts:", dict(scripts.most_common(40)))
