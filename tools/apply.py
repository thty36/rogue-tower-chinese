# -*- coding: utf-8 -*-
"""Apply Chinese translations + font replacement to Rogue Tower assets.

Usage:
  python apply.py --strings translations.json --font font.ttf --out OUTDIR
Works on copies of the game files placed alongside this script's input dir.
Only replaces length-prefixed strings whose 4-byte alignment padding checks out.
"""
import sys, io, json, struct, argparse
from pathlib import Path
import UnityPy

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

GAME = Path(r"D:\Steam\steamapps\common\Rogue Tower\Rogue Tower_Data")
FILES = ["level0", "level1", "sharedassets0.assets", "sharedassets1.assets",
         "globalgamemanagers.assets"]

ID_SLOT_CLASSES = {"UpgradeButton", "TowerUpgradeCard", "DOTUpgradeCard",
                   "ManaGenUpgradeCard", "MaxHealthUpgradeCard", "TreeUpgradeCard",
                   "HauntedHouseUpgrade", "UniversityUpgrade", "TowerUnlockCard"}
SKIP_CLASSES = {"AchievementManager", "Button", "Slider", "Toggle", "Image", "Mask",
                "CanvasScaler", "GraphicRaycaster", "Bloom", "PostProcessProfile",
                "StandaloneInputModule", "EventSystem"}

def scan_aligned_strings(blob: bytes):
    """Yield (offset, length, text) for alignment-valid length-prefixed strings."""
    out = []
    i, n = 0, len(blob)
    while i + 4 <= n:
        ln = struct.unpack_from("<i", blob, i)[0]
        if 1 <= ln <= 4096 and i + 4 + ln <= n:
            chunk = blob[i + 4:i + 4 + ln]
            try:
                text = chunk.decode("utf-8")
            except UnicodeDecodeError:
                text = None
            if text and all(c in "\n\t" or 0x20 <= ord(c) < 0x7F or ord(c) > 0x2E7F for c in text):
                pad = (4 - ln % 4) % 4
                if ln % 4 == 0 or blob[i + 4 + ln:i + 4 + ln + pad] == b"\x00" * pad:
                    out.append((i, ln, text))
                    i += 4 + ln + pad
                    continue
        i += 4
    return out

def apply_to_blob(blob: bytes, tr: dict, cls: str):
    """Replace strings found in blob per translation dict. Returns (new_blob, n_replaced)."""
    hits = [(o, l, t) for (o, l, t) in scan_aligned_strings(blob) if o >= 28]
    if cls in SKIP_CLASSES:
        return blob, 0
    if cls in ID_SLOT_CLASSES and hits:
        hits = hits[1:]  # first post-header string is an internal ID — never touch
    hits = [h for h in hits if h[2] in tr]
    if not hits:
        return blob, 0
    # rebuild blob: copy segments, replacing from the hit list (sorted by offset)
    parts, pos, count = [], 0, 0
    for off, ln, text in hits:
        parts.append(blob[pos:off])
        enc = tr[text].encode("utf-8")
        newpad = b"\x00" * ((4 - len(enc) % 4) % 4)
        parts.append(struct.pack("<i", len(enc)) + enc + newpad)
        oldpad = (4 - ln % 4) % 4
        pos = off + 4 + ln + oldpad
        count += 1
    parts.append(blob[pos:])
    return b"".join(parts), count

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strings", default=None)
    ap.add_argument("--font", default=None)
    ap.add_argument("--src", default=str(GAME))
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", default=None, help="comma list of files to process")
    args = ap.parse_args()

    src = Path(args.src)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    tr = {}
    if args.strings:
        tr = json.loads(Path(args.strings).read_text(encoding="utf-8"))
        print(f"loaded {len(tr)} translations")

    files = args.only.split(",") if args.only else FILES
    for fname in files:
        p = src / fname
        if not p.exists():
            print(f"skip missing {fname}")
            continue
        env = UnityPy.load(str(p))
        replaced = 0
        touched = False
        for obj in env.objects:
            if obj.type.name == "MonoBehaviour":
                try:
                    cls = obj.read(check_read=False).m_Script.read().m_ClassName
                except Exception:
                    cls = "?"
                blob = obj.get_raw_data()
                new_blob, n = apply_to_blob(blob, tr, cls)
                if n:
                    obj.set_raw_data(new_blob)
                    replaced += n
                    touched = True
            elif obj.type.name == "Font" and args.font:
                f = obj.read()
                font_bytes = Path(args.font).read_bytes()
                f.m_FontData = font_bytes
                try:
                    f.m_CharacterRects = []
                except Exception:
                    pass
                f.save()
                touched = True
                print(f"  replaced font '{f.m_Name}' data: {len(font_bytes)} bytes")
        if not touched:
            print(f"{fname}: nothing to change, copying as-is")
            (out / fname).write_bytes(p.read_bytes())
        else:
            ret = env.save(out_path=str(out))
            print(f"{fname}: replaced {replaced} strings -> {out / fname} (save ret: {type(ret).__name__})")

if __name__ == "__main__":
    main()
