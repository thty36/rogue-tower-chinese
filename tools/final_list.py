# -*- coding: utf-8 -*-
"""Final translatable string list: excludes internal IDs and ID slots."""
import sys, io, json, struct, re
from pathlib import Path
import UnityPy

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
GAME = Path(r"D:\Steam\steamapps\common\Rogue Tower\Rogue Tower_Data")
OUT = Path(__file__).resolve().parent.parent

# classes whose FIRST string (smallest offset >= 28) is an internal ID
ID_SLOT_CLASSES = {"UpgradeButton", "TowerUpgradeCard", "DOTUpgradeCard",
                   "ManaGenUpgradeCard", "MaxHealthUpgradeCard", "TreeUpgradeCard",
                   "HauntedHouseUpgrade", "UniversityUpgrade", "TowerUnlockCard"}
# classes whose strings are all internal IDs / engine internals
SKIP_CLASSES = {"AchievementManager", "Button", "Slider", "Toggle", "Image", "Mask",
                "CanvasScaler", "GraphicRaycaster", "Bloom", "PostProcessProfile",
                "StandaloneInputModule", "EventSystem"}
# only these classes contribute translatable display text
TRANSLATE_CLASSES = {"Text", "BattleCry", "DOTUpgradeCard", "Enemy",
                     "HauntedHouseUpgrade", "LevelLoader", "ManaGenUpgradeCard",
                     "MaxHealthUpgradeCard", "MonsterUpgradeCard", "SecretMessage",
                     "SpawnManager", "TowerUnlockCard", "TowerUpgradeCard",
                     "TreeUpgradeCard", "UniversityUpgrade"}
# strict internal-ID pattern e.g. BallistaSlow1, GlobalArmor1, HauntedHouse
ID_RE = re.compile(r"^[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]*)+\d*$")

def strings_of(blob):
    out = []
    i, n = 0, len(blob)
    while i + 4 <= n:
        ln = struct.unpack_from("<i", blob, i)[0]
        if 1 <= ln <= 4096 and i + 4 + ln <= n:
            try:
                t = blob[i + 4:i + 4 + ln].decode("utf-8")
                if all(c in "\n\t" or 0x20 <= ord(c) < 0x7F for c in t):
                    pad = (4 - ln % 4) % 4
                    if ln % 4 == 0 or blob[i + 4 + ln:i + 4 + ln + pad] == b"\x00" * pad:
                        out.append((i, t))
                        i += 4 + ln + pad
                        continue
            except UnicodeDecodeError:
                pass
        i += 4
    return out

def plausible(s):
    if not s.strip():
        return False
    if ID_RE.match(s):
        return False
    if not re.search(r"[A-Za-z]{2,}", s):
        return False
    if re.search(r"(.)\1{5,}", s):
        return False
    # reject junk: mostly non-letter symbols
    letters = sum(c.isalpha() or c.isspace() for c in s)
    if letters < len(s) * 0.5:
        return False
    return True

cand = {}
for fname in ["level0", "level1", "sharedassets0.assets", "sharedassets1.assets"]:
    env = UnityPy.load(str(GAME / fname))
    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        try:
            cls = obj.read(check_read=False).m_Script.read().m_ClassName
        except Exception:
            continue
        if cls in SKIP_CLASSES or cls not in TRANSLATE_CLASSES:
            continue
        ss = [s for s in strings_of(obj.get_raw_data()) if s[0] >= 28]
        if cls in ID_SLOT_CLASSES and ss:
            ss = ss[1:]  # drop ID slot
        for off, t in ss:
            if plausible(t):
                cand.setdefault(t, {"count": 0, "classes": set()})
                cand[t]["count"] += 1
                cand[t]["classes"].add(cls)

res = {t: {"count": v["count"], "classes": sorted(v["classes"])}
       for t, v in sorted(cand.items(), key=lambda kv: -kv[1]["count"])}
(OUT / "final_candidates.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
keys = list(res.keys())
(OUT / "final_keys.txt").write_text("\n".join(keys), encoding="utf-8")
print("final translatable unique strings:", len(keys))
