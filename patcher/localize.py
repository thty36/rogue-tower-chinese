# -*- coding: utf-8 -*-
"""
Rogue Tower 一键汉化补丁工具

功能：
  1. 自动定位 Steam 安装的 Rogue Tower 游戏目录
  2. 备份原始资源文件（backup_original/）
  3. 将中文文本写回 Unity 资源，并内嵌思源黑体（支持中文渲染）
  4. 校验产物完整性后安装
  5. 通过 Steam 协议启动游戏

用法：
  python localize.py                # 汉化并启动游戏
  python localize.py --game 路径     # 指定游戏目录（Rogue Tower 安装目录）
  python localize.py --no-launch    # 只汉化，不启动
  python localize.py --restore      # 还原为英文原版
  python localize.py --reapply      # 已汉化时强制重新汉化
"""
import argparse
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import UnityPy
except ImportError:
    print("[错误] 缺少依赖 UnityPy，请先运行: pip install -r requirements.txt")
    sys.exit(1)

REPO_ROOT = Path(__file__).resolve().parent.parent
RESOURCES = REPO_ROOT / "resources"
TRANSLATIONS = RESOURCES / "translations.json"
FONT = RESOURCES / "NotoSansSC-Regular.otf"

GAME_DATA_FILES = ["level0", "level1", "sharedassets0.assets", "sharedassets1.assets"]
STEAM_APPID = "1843760"

# 组件类型规则（与提取阶段保持一致）
ID_SLOT_CLASSES = {"UpgradeButton", "TowerUpgradeCard", "DOTUpgradeCard",
                   "ManaGenUpgradeCard", "MaxHealthUpgradeCard", "TreeUpgradeCard",
                   "HauntedHouseUpgrade", "UniversityUpgrade", "TowerUnlockCard"}
SKIP_CLASSES = {"AchievementManager", "Button", "Slider", "Toggle", "Image", "Mask",
                "CanvasScaler", "GraphicRaycaster", "Bloom", "PostProcessProfile",
                "StandaloneInputModule", "EventSystem"}

ID_RE = re.compile(r"^[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]*)+\d*$")
CJK_RE = re.compile(rb"[\xe4-\xe9][\x80-\xbf][\x80-\xbf]")  # CJK 基本区 UTF-8 三字节序列


def scan_aligned_strings(blob: bytes):
    """扫描 4 字节对齐的“长度前缀+UTF-8”字符串（Unity 序列化格式）。"""
    out = []
    i, n = 0, len(blob)
    while i + 4 <= n:
        ln = struct.unpack_from("<i", blob, i)[0]
        if 1 <= ln <= 4096 and i + 4 + ln <= n:
            try:
                text = blob[i + 4:i + 4 + ln].decode("utf-8")
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
    """按翻译词典替换组件数据中的字符串，返回 (新数据, 替换数)。"""
    hits = [(o, l, t) for (o, l, t) in scan_aligned_strings(blob) if o >= 28]
    if cls in SKIP_CLASSES:
        return blob, 0
    if cls in ID_SLOT_CLASSES and hits:
        hits = hits[1:]  # 第一个字符串是内部升级 ID，绝不能动
    hits = [h for h in hits if h[2] in tr]
    if not hits:
        return blob, 0
    parts, pos, count = [], 0, 0
    for off, ln, text in hits:
        parts.append(blob[pos:off])
        enc = tr[text].encode("utf-8")
        newpad = b"\x00" * ((4 - len(enc) % 4) % 4)
        parts.append(struct.pack("<i", len(enc)) + enc + newpad)
        pos = off + 4 + ln + (4 - ln % 4) % 4
        count += 1
    parts.append(blob[pos:])
    return b"".join(parts), count


def find_steam_libraries():
    """从注册表与 libraryfolders.vdf 收集所有 Steam 库目录。"""
    libs = []
    try:
        import winreg
        for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
                try:
                    key = winreg.OpenKey(root, r"Software\Valve\Steam", 0, winreg.KEY_QUERY_VALUE | view)
                    val, _ = winreg.QueryValueEx(key, "SteamPath")
                    if val:
                        libs.append(Path(val))
                    winreg.CloseKey(key)
                except OSError:
                    pass
                except FileNotFoundError:
                    pass
    except ImportError:
        pass
    libs.append(Path(r"C:\Program Files (x86)\Steam"))
    seen, result = set(), []
    for lib in libs:
        vdf = lib / "steamapps" / "libraryfolders.vdf"
        if vdf.exists():
            for m in re.finditer(r'"path"\s+"([^"]+)"', vdf.read_text(encoding="utf-8", errors="ignore")):
                p = Path(m.group(1).replace("\\\\", "\\"))
                if str(p).lower() not in seen:
                    seen.add(str(p).lower())
                    result.append(p)
        if str(lib).lower() not in seen:
            seen.add(str(lib).lower())
            result.append(lib)
    return result


def find_game_installations():
    """返回所有找到的 Rogue Tower 安装目录列表。"""
    found = []
    for lib in find_steam_libraries():
        game = lib / "steamapps" / "common" / "Rogue Tower"
        if (game / "Rogue Tower_Data" / "level0").is_file():
            found.append(game)
    return found


def is_localized(data_dir: Path) -> bool:
    """粗略判断 level0 是否已包含中文。"""
    try:
        data = (data_dir / "level0").read_bytes()
    except OSError:
        return False
    return "开始游戏".encode("utf-8") in data or "怪物图鉴".encode("utf-8") in data


def game_is_running() -> bool:
    try:
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq Rogue Tower.exe"],
                             capture_output=True, timeout=15).stdout
        return b"Rogue Tower.exe" in out
    except Exception:
        return False


def do_backup(data_dir: Path):
    backup = data_dir / "backup_original"
    if (backup / "level0").is_file():
        print("[备份] backup_original 已存在，跳过备份")
        return backup
    backup.mkdir(exist_ok=True)
    for f in GAME_DATA_FILES:
        src = data_dir / f
        if src.is_file():
            shutil.copy2(src, backup / f)
    print(f"[备份] 原始文件已备份到 {backup}")
    return backup


def do_restore(data_dir: Path):
    backup = data_dir / "backup_original"
    if not (backup / "level0").is_file():
        print("[错误] 找不到备份目录 backup_original，无法还原")
        sys.exit(1)
    if game_is_running():
        print("[错误] 游戏正在运行，请先关闭游戏再还原")
        sys.exit(1)
    for f in GAME_DATA_FILES:
        src = backup / f
        if src.is_file():
            shutil.copy2(src, data_dir / f)
    print("[还原] 已恢复为英文原版")


def do_patch(data_dir: Path, tr: dict):
    """在临时目录生成汉化资源并校验，成功后安装到游戏目录。"""
    font_bytes = FONT.read_bytes()
    tmp = Path(tempfile.mkdtemp(prefix="rt_cn_"))
    total_replaced = 0
    try:
        for fname in GAME_DATA_FILES:
            src = data_dir / fname
            if not src.is_file():
                print(f"[警告] 缺少 {fname}，跳过")
                continue
            env = UnityPy.load(str(src))
            replaced, touched = 0, False
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
                elif obj.type.name == "Font" and fname == "sharedassets0.assets":
                    f = obj.read()
                    f.m_FontData = font_bytes
                    f.save()
                    touched = True
                    print(f"[字体] 已将 '{f.m_Name}' 内嵌字体替换为思源黑体 ({len(font_bytes)//1024} KB)")
            if not touched:
                continue
            env.save(out_path=str(tmp))
            total_replaced += replaced
            print(f"[汉化] {fname}: 替换 {replaced} 处文本")

        # ---- 校验（字节级，不依赖外部资源文件） ----
        problems = []
        for fname in GAME_DATA_FILES:
            out_f = tmp / fname
            if not out_f.is_file():
                if fname in ("level0", "level1"):
                    problems.append(f"{fname} 未生成")
                continue
            data = out_f.read_bytes()
            n_obj_new = count_objects(out_f)
            n_obj_old = count_objects(data_dir / fname)
            if n_obj_new != n_obj_old:
                problems.append(f"{fname} 对象数不一致 ({n_obj_old} -> {n_obj_new})")
            cjk = len(CJK_RE.findall(data))
            if fname in ("level0", "level1", "sharedassets1.assets") and cjk < 500:
                problems.append(f"{fname} 中文字节数异常偏少 ({cjk})")
        if not (tmp / "level1").is_file() or b"BallistaSlow1" not in (tmp / "level1").read_bytes():
            problems.append("level1 内部升级 ID 丢失，文件可能损坏")
        if (tmp / "sharedassets0.assets").is_file():
            if b"OTTO" not in (tmp / "sharedassets0.assets").read_bytes():
                problems.append("sharedassets0.assets 字体数据异常")
        if problems:
            print("[校验失败] 未安装，游戏文件保持原样：")
            for p in problems:
                print("   -", p)
            sys.exit(2)
        print(f"[校验] 通过（共替换 {total_replaced} 处文本），正在安装到游戏目录…")

        if game_is_running():
            print("[错误] 检测到游戏正在运行，请关闭游戏后重新运行本脚本")
            sys.exit(1)
        for fname in GAME_DATA_FILES:
            out_f = tmp / fname
            if out_f.is_file():
                shutil.copy2(out_f, data_dir / fname)
        print("[安装] 汉化完成！")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def count_objects(path):
    """统计资源文件对象数量（仅遍历，不读取内容，无需外部依赖文件）。"""
    env = UnityPy.load(str(path))
    return sum(1 for _ in env.objects)


def launch_game(game_dir: Path):
    print(f"[启动] 正在通过 Steam 启动 Rogue Tower …")
    try:
        os.startfile(f"steam://rungameid/{STEAM_APPID}")
    except Exception:
        try:
            subprocess.Popen([str(game_dir / "Rogue Tower.exe")], cwd=str(game_dir))
        except Exception as e:
            print(f"[警告] 无法启动游戏：{e}")
            print(f"       请手动启动：{game_dir / 'Rogue Tower.exe'}")


def choose_game(args_game):
    candidates = []
    if args_game:
        p = Path(args_game)
        if (p / "Rogue Tower_Data" / "level0").is_file():
            return p
        if (p / "level0").is_file():
            return p.parent
        print(f"[错误] {args_game} 下找不到 Rogue Tower_Data，请确认路径")
        sys.exit(1)
    env_dir = os.environ.get("RT_GAME_DIR")
    if env_dir and (Path(env_dir) / "Rogue Tower_Data" / "level0").is_file():
        return Path(env_dir)
    try:
        candidates = find_game_installations()
    except Exception:
        candidates = []
    if not candidates:
        print("[提示] 未能自动找到游戏，请手动输入 Rogue Tower 的安装目录")
        print("       （即包含 Rogue Tower.exe 和 Rogue Tower_Data 的文件夹）")
        try:
            s = input("游戏目录: ").strip().strip('"')
        except EOFError:
            sys.exit(1)
        if not s:
            sys.exit(1)
        p = Path(s)
        if (p / "Rogue Tower_Data" / "level0").is_file():
            return p
        print("[错误] 该目录无效")
        sys.exit(1)
    if len(candidates) == 1:
        print(f"[定位] 找到游戏: {candidates[0]}")
        return candidates[0]
    print("[定位] 找到多个安装：")
    for i, c in enumerate(candidates, 1):
        print(f"   {i}. {c}")
    try:
        idx = int(input("请选择序号 [1]: ").strip() or "1")
    except (ValueError, EOFError):
        idx = 1
    return candidates[max(1, min(idx, len(candidates))) - 1]


def main():
    ap = argparse.ArgumentParser(description="Rogue Tower 中文汉化补丁")
    ap.add_argument("--game", help="游戏安装目录（留空则自动检测）")
    ap.add_argument("--no-launch", action="store_true", help="汉化后不启动游戏")
    ap.add_argument("--restore", action="store_true", help="还原英文原版")
    ap.add_argument("--reapply", action="store_true", help="已汉化时强制重新汉化")
    args = ap.parse_args()

    print("=" * 52)
    print("  Rogue Tower 中文汉化  (Steam AppID 1843760)")
    print("=" * 52)

    game_dir = choose_game(args.game)
    data_dir = game_dir / "Rogue Tower_Data"

    if args.restore:
        do_restore(data_dir)
        return

    if is_localized(data_dir) and not args.reapply:
        print("[状态] 游戏已是汉化版本，无需重复操作")
        if not args.no_launch:
            launch_game(game_dir)
        return

    if game_is_running():
        print("[错误] 游戏正在运行，请先关闭游戏后重新运行本脚本")
        sys.exit(1)

    if not TRANSLATIONS.is_file():
        print(f"[错误] 找不到翻译词典 {TRANSLATIONS}")
        sys.exit(1)
    if not FONT.is_file():
        print(f"[错误] 找不到字体文件 {FONT}")
        sys.exit(1)

    tr = json.loads(TRANSLATIONS.read_text(encoding="utf-8"))
    print(f"[词典] 载入 {len(tr)} 条翻译")

    do_backup(data_dir)
    do_patch(data_dir, tr)

    if not args.no_launch:
        launch_game(game_dir)
    else:
        print("[完成] 可随时从 Steam 启动游戏")


if __name__ == "__main__":
    main()
