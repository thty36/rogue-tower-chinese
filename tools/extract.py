# -*- coding: utf-8 -*-
"""Extract all length-prefixed strings from MonoBehaviour objects in game assets.

Verifies 4-byte alignment padding convention, outputs a manifest JSON.
"""
import sys, io, json, struct
from pathlib import Path
import UnityPy

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
GAME = Path(r"D:\Steam\steamapps\common\Rogue Tower\Rogue Tower_Data")
OUT = Path(__file__).resolve().parent.parent
FILES = ["level0", "level1", "sharedassets0.assets", "sharedassets1.assets",
         "globalgamemanagers.assets"]

def scan_strings(blob: bytes):
    """Find (offset, string) pairs where a plausible length-prefixed UTF-8 string lives.
    Returns list of (offset, length, text, padded_len_with_alignment)."""
    out = []
    n = len(blob)
    i = 0
    while i + 4 <= n:
        ln = struct.unpack_from("<i", blob, i)[0]
        if 1 <= ln <= 1024 and i + 4 + ln <= n:
            chunk = blob[i + 4:i + 4 + ln]
            try:
                text = chunk.decode("utf-8")
            except UnicodeDecodeError:
                i += 4
                continue
            # plausible text: printable + whitespace, no NUL
            if text and all(c == "\n" or c == "\t" or ord(c) >= 0x20 for c in text):
                pad = (4 - (4 + ln) % 4) % 4  # data after length must align to 4
                padded = 4 + ln + pad
                out.append((i, ln, text, padded))
                i += padded
                continue
        i += 4
    return out

manifest = []
pad_stats = {"padded_ok": 0, "no_pad_needed": 0, "pad_mismatch": 0}
for fname in FILES:
    env = UnityPy.load(str(GAME / fname))
    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        try:
            d = obj.read(check_read=False)
            cls = d.m_Script.read().m_ClassName
        except Exception:
            cls = "?"
        blob = obj.get_raw_data()
        for (off, ln, text, padded) in scan_strings(blob):
            # verify alignment convention on original data
            if ln % 4 == 0:
                pad_stats["no_pad_needed"] += 1
            else:
                exp_pad = (4 - ln % 4) % 4
                actual = blob[4 + off + ln: 4 + off + ln + exp_pad]
                if actual == b"\x00" * exp_pad:
                    pad_stats["padded_ok"] += 1
                else:
                    pad_stats["pad_mismatch"] += 1
            manifest.append({
                "file": fname, "path_id": obj.path_id, "class": cls,
                "offset": off, "len": ln, "text": text,
            })

(OUT / "string_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
uniq = sorted(set(m["text"] for m in manifest), key=lambda s: (len(s), s))
(OUT / "unique_strings.json").write_text(json.dumps(uniq, ensure_ascii=False, indent=1), encoding="utf-8")
print("alignment stats:", pad_stats)
print("total occurrences:", len(manifest))
print("unique strings:", len(uniq))
from collections import Counter
c = Counter(m["class"] for m in manifest)
print("by class:", c.most_common(30))
