# -*- coding: utf-8 -*-
"""从 translations.json 生成 C# 词典源码（嵌入插件，免运行时解析 JSON）。"""
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "mod_build" / "LangTable.cs"


def csharp_str(s: str) -> str:
    out = []
    for ch in s:
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        elif ord(ch) < 0x20:
            out.append(f"\\u{ord(ch):04x}")
        else:
            out.append(ch)
    return '"' + "".join(out) + '"'


def main():
    tr = json.loads((BASE / "resources" / "translations.json").read_text(encoding="utf-8"))
    lines = [
        "// 自动生成：请勿手改（tools/gen_langtable.py）",
        "using System.Collections.Generic;",
        "",
        "public static class LangTable",
        "{",
        "    public static void Fill(Dictionary<string,string> d)",
        "    {",
    ]
    for k, v in tr.items():
        lines.append(f"        d.Add({csharp_str(k)}, {csharp_str(v)});")
    lines += ["    }", "}", ""]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"written {OUT} with {len(tr)} entries")


if __name__ == "__main__":
    main()
