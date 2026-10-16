# -*- coding: utf-8 -*-
"""Verify alignment on known-real strings; build curated candidate list."""
import sys, io, json, struct, re
from pathlib import Path
import UnityPy

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
GAME = Path(r"D:\Steam\steamapps\common\Rogue Tower\Rogue Tower_Data")
OUT = Path(r"C:\Users\fanchengpeng\.zcode\workspace\default\rogue-tower-cn")

# classes that genuinely hold display text
TEXT_CLASSES = {"Text","UpgradeButton","TowerUpgradeCard","MonsterUpgradeCard",
                "DOTUpgradeCard","TowerUnlockCard","SecretMessage","BattleCry",
                "MonsterManualEntry","SimpleUI","TowerFlyweight","BuildButtonUI",
                "ManaGenUpgradeCard","MaxHealthUpgradeCard","TreeUpgradeCard",
                "HauntedHouseUpgrade","UniversityUpgrade","PauseMenu","OptionsMenu",
                "MainMenu","PlayMenu","LevelLoader","Enemy","SpawnableObject",
                "SpawnManager","Shrine","House","IncomeGenerator","ManaCrystal",
                "AchievementManager","TowerUI","UniBonusUI","DevelopmentManager"}

# verify padding for real-looking strings inside these classes
real_check = {"ok":0,"bad":0}
per_class = {}
for fname in ["level0","level1","sharedassets0.assets","sharedassets1.assets"]:
    env = UnityPy.load(str(GAME / fname))
    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        try:
            cls = obj.read(check_read=False).m_Script.read().m_ClassName
        except Exception:
            continue
        if cls not in TEXT_CLASSES:
            continue
        blob = obj.get_raw_data()
        i = 0
        n = len(blob)
        while i + 4 <= n:
            ln = struct.unpack_from("<i", blob, i)[0]
            if 1 <= ln <= 1024 and i + 4 + ln <= n:
                chunk = blob[i+4:i+4+ln]
                try:
                    text = chunk.decode("utf-8")
                    if text and all(c in "\n\t" or ord(c) >= 0x20 for c in text):
                        # treat as candidate; verify pad
                        if ln % 4:
                            exp = (4 - ln % 4) % 4
                            actual = blob[i+4+ln:i+4+ln+exp]
                            if actual == b"\x00"*exp: real_check["ok"] += 1
                            else: real_check["bad"] += 1
                        else:
                            real_check["ok"] += 1
                        per_class.setdefault(cls, {}).setdefault(text, 0)
                        per_class[cls][text] += 1
                        i += 4 + ln + ((4 - ln % 4) % 4)
                        continue
                except UnicodeDecodeError:
                    pass
            i += 4

print("padding verification (text classes only):", real_check)

# candidates: filter junk-looking strings
def plausible(s):
    if not s.strip(): return False
    letters = sum(c.isalpha() for c in s)
    if letters == 0: return False             # pure digits/symbols like "+10%"
    if letters < len(s) * 0.4:                # mostly symbols
        # allow things like "x2 Damage", "$100", "+5"
        if not re.search(r"[A-Za-z]{2,}", s): return False
    if re.fullmatch(r"[\x20-\x7e]", ""): return False
    # reject control-ish junk: long runs of repeated chars
    if re.search(r"(.)\1{5,}", s): return False
    if not re.search(r"[A-Za-z]{2,}", s): return False
    return True

cand = {}
for cls, texts in per_class.items():
    for t, cnt in texts.items():
        if plausible(t):
            cand.setdefault(t, {"count":0,"classes":set()})
            cand[t]["count"] += cnt
            cand[t]["classes"].add(cls)

for t in cand:
    cand[t]["classes"] = sorted(cand[t]["classes"])

print("plausible unique strings:", len(cand))
json_out = {t: v for t, v in sorted(cand.items(), key=lambda kv: -kv[1]["count"])}
(OUT / "candidates.json").write_text(json.dumps(json_out, ensure_ascii=False, indent=1), encoding="utf-8")
print("written candidates.json")
