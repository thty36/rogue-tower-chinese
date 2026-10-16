# -*- coding: utf-8 -*-
"""
Rogue Tower 汉化安装器（BepInEx 运行时翻译方案）

流程：
  1. 自动定位游戏
  2. 若游戏资源已被旧版"资源汉化"修改过 → 从 backup_original 还原英文原版
  3. 安装 BepInEx(x86) + 语言切换插件到游戏目录
  4. 通过 Steam 启动游戏（默认中文，右上角 中/EN 按钮随时切换）

用法：
  python install_mod.py                # 安装并启动
  python install_mod.py --no-launch    # 只安装
  python install_mod.py --restore      # 卸载汉化（移除 BepInEx + 还原英文）
"""
import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MOD_PACKAGE = REPO_ROOT / "mod_package"
BEPINEX_ZIP = MOD_PACKAGE / "BepInEx_win_x86_5.4.23.2.zip"
PLUGIN_DLL = MOD_PACKAGE / "LangTogglePlugin.dll"

GAME_DATA_FILES = ["level0", "level1", "sharedassets0.assets", "sharedassets1.assets"]
STEAM_APPID = "1843760"

# 复用 localize.py 的游戏定位逻辑
sys.path.insert(0, str(Path(__file__).parent))
from localize import find_game_installations, is_localized, game_is_running, launch_game, choose_game


def ensure_english(data_dir: Path) -> bool:
    """资源若被旧版资源汉化修改，从备份还原英文。返回是否处于英文状态。"""
    if not is_localized(data_dir):
        return True
    backup = data_dir / "backup_original"
    if not (backup / "level0").is_file():
        print("[错误] 检测到游戏资源已被旧版汉化修改，但找不到 backup_original 备份。")
        print("       请在 Steam 中对该游戏执行「验证文件完整性」恢复英文后，重新运行本脚本。")
        return False
    for f in GAME_DATA_FILES:
        src = backup / f
        if src.is_file():
            shutil.copy2(src, data_dir / f)
    print("[还原] 已从备份恢复英文原版资源（汉化改由插件在运行时完成，游戏文件保持原版）")
    return True


def install_mod(game_dir: Path):
    data_dir = game_dir / "Rogue Tower_Data"
    if not BEPINEX_ZIP.is_file() or not PLUGIN_DLL.is_file():
        print(f"[错误] 仓库缺少 mod_package 文件: {BEPINEX_ZIP.name} / {PLUGIN_DLL.name}")
        sys.exit(1)
    if not ensure_english(data_dir):
        sys.exit(2)
    if game_is_running():
        print("[错误] 游戏正在运行，请先关闭游戏后重新运行本脚本")
        sys.exit(1)

    # 解压 BepInEx 到游戏根目录（winhttp.dll / doorstop_config.ini / .doorstop_version / BepInEx/）
    with zipfile.ZipFile(BEPINEX_ZIP) as z:
        z.extractall(game_dir)
    plugins = game_dir / "BepInEx" / "plugins"
    plugins.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PLUGIN_DLL, plugins / PLUGIN_DLL.name)
    print(f"[安装] BepInEx 5.4.23.2 (x86) + 语言切换插件 -> {game_dir}")
    print("[说明] 游戏默认显示中文；点击游戏右上角 中/EN 按钮可随时切换中英文")


def restore_all(game_dir: Path):
    data_dir = game_dir / "Rogue Tower_Data"
    if game_is_running():
        print("[错误] 游戏正在运行，请先关闭游戏后重新运行本脚本")
        sys.exit(1)
    # 移除 BepInEx 注入组件
    for f in ["winhttp.dll", "doorstop_config.ini", ".doorstop_version"]:
        p = game_dir / f
        if p.exists():
            p.unlink()
    bepinex = game_dir / "BepInEx"
    if bepinex.exists():
        shutil.rmtree(bepinex, ignore_errors=True)
    # 还原英文资源
    ensure_english(data_dir)
    print("[还原] 已卸载汉化：移除 BepInEx 并恢复英文原版")


def main():
    ap = argparse.ArgumentParser(description="Rogue Tower 汉化安装器（BepInEx 插件方案）")
    ap.add_argument("--game", help="游戏安装目录（留空则自动检测）")
    ap.add_argument("--no-launch", action="store_true", help="安装后不启动游戏")
    ap.add_argument("--restore", action="store_true", help="卸载汉化，恢复英文原版")
    args = ap.parse_args()

    print("=" * 52)
    print("  Rogue Tower 中文汉化安装器（运行时翻译 + 中/EN 切换）")
    print("=" * 52)

    game_dir = choose_game(args.game)

    if args.restore:
        restore_all(game_dir)
        return

    if (game_dir / "BepInEx" / "plugins" / PLUGIN_DLL.name).is_file() and \
       (game_dir / "winhttp.dll").is_file():
        print("[状态] 汉化插件已安装，无需重复安装")
    else:
        install_mod(game_dir)

    if not args.no_launch:
        launch_game(game_dir)
    else:
        print("[完成] 可随时从 Steam 启动游戏")


if __name__ == "__main__":
    main()
