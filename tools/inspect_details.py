# -*- coding: utf-8 -*-
"""Inspect the Font object and sample MonoBehaviours to find text fields."""
import sys, io
from pathlib import Path
import UnityPy

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
GAME = Path(r"D:\Steam\steamapps\common\Rogue Tower\Rogue Tower_Data")

# 1. font details
env = UnityPy.load(str(GAME / "sharedassets0.assets"))
for obj in env.objects:
    if obj.type.name == "Font":
        f = obj.read()
        print("FONT:", f.m_Name, "| lineSpacing:", f.m_LineSpacing,
              "| characterRects:", len(f.m_CharacterRects) if f.m_CharacterRects else 0,
              "| fontSize:", f.m_FontSize, "| fontNames:", f.m_FontNames,
              "| fallbackFonts:", getattr(f, "m_FallbackFonts", None))
        try:
            raw = obj.get_raw_data()
            # peek ascii strings in raw font data
            import re
            ss = [m.decode() for m in re.findall(rb"[\x20-\x7e]{4,}", raw)]
            print("  raw strings:", ss[:20])
        except Exception as e:
            print("  raw read err", e)

# 2. what fonts do Text components reference
seen = {}
for obj in env.objects:
    if obj.type.name == "MonoBehaviour":
        try:
            d = obj.read(check_read=False)
            cls = d.m_Script.read().m_ClassName
        except Exception:
            continue
        if cls == "Text" and "fontref" not in seen:
            try:
                t = obj.read_typetree()
                seen["fontref"] = t.get("m_FontData", {}).get("m_Font")
                print("sample Text m_FontData.m_Font:", seen["fontref"])
                print("sample Text fontName:", t.get("m_FontData", {}).get("m_Font"))
            except Exception as e:
                print("tt err", e)

# 3. sample custom components' typetrees
from collections import defaultdict
samples = defaultdict(list)
WANT = {"UpgradeButton","MonsterManualEntry","TowerUpgradeCard","MonsterUpgradeCard",
        "DOTUpgradeCard","TowerUnlockCard","SecretMessage","BattleCry","SimpleUI",
        "TowerFlyweight","BuildButtonUI","House","Shrine","Enemy","PauseMenu",
        "OptionsMenu","MainMenu","ManaGenUpgradeCard","MaxHealthUpgradeCard",
        "TreeUpgradeCard","HauntedHouseUpgrade","UniversityUpgrade","IncomeGenerator"}
for fname in ["level0","level1","sharedassets0.assets","sharedassets1.assets"]:
    env = UnityPy.load(str(GAME / fname))
    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        try:
            d = obj.read(check_read=False)
            cls = d.m_Script.read().m_ClassName
        except Exception:
            continue
        if cls in WANT and len(samples[cls]) < 2:
            try:
                tt = obj.read_typetree()
                samples[cls].append((fname, tt))
            except Exception as e:
                pass

for cls, items in samples.items():
    print(f"\n===== {cls} =====")
    fname, tt = items[0]
    print(f"({fname})")
    for k, v in tt.items():
        if k in ("m_GameObject","m_ObjectHideFlags","m_CorrespondingSourceObject","m_PrefabInstance","m_PrefabAsset"):
            continue
        s = str(v)
        print(f"  {k} = {s[:160]}")
