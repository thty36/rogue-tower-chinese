import sys
from pathlib import Path

CONTENT = r'''@echo off
setlocal
set "PYTHONIOENCODING=gbk"
cd /d "%~dp0"
title Rogue Tower 一键汉化

echo ============================================
echo   Rogue Tower 中文汉化 一键脚本
echo   首次运行需要联网安装依赖(约 1 分钟)
echo ============================================
echo.

rem ---- 1. 检查 Python ----
set "PYCMD="
py -3 -c "import sys;assert sys.version_info>=(3,8)" >nul 2>nul && set "PYCMD=py -3"
if not defined PYCMD python -c "import sys;assert sys.version_info>=(3,8)" >nul 2>nul && set "PYCMD=python"
if not defined PYCMD python3 -c "import sys;assert sys.version_info>=(3,8)" >nul 2>nul && set "PYCMD=python3"
if defined RT_PYTHON set "PYCMD=%RT_PYTHON%"
if not defined PYCMD (
    echo [错误] 未检测到可用的 Python 3.8+。
    echo        请安装 Python 并勾选 Add to PATH 后重试:
    echo        https://www.python.org/downloads/
    start https://www.python.org/downloads/
    pause
    exit /b 1
)

rem ---- 2. 准备 Python 环境(优先虚拟环境, 失败则装到用户目录) ----
set "RTPY="
if not exist ".venv\Scripts\python.exe" (
    echo [环境] 正在创建 Python 虚拟环境...
    %PYCMD% -m venv .venv >nul 2>nul
)
if exist ".venv\Scripts\python.exe" (
    set "RTPY=.venv\Scripts\python.exe"
) else (
    echo [环境] 虚拟环境不可用, 改用用户目录安装依赖...
    %PYCMD% -m pip install --user --quiet -r patcher\requirements.txt
    if errorlevel 1 (
        echo [错误] 依赖安装失败, 请检查 Python 环境和网络后重试
        pause
        exit /b 1
    )
    set "RTPY=%PYCMD%"
)
if not exist ".venv\Scripts\.deps_ok" if ".venv\Scripts\python.exe"=="%RTPY%" (
    echo [环境] 正在安装依赖 UnityPy ...
    "%RTPY%" -m pip install --quiet -r patcher\requirements.txt
    if errorlevel 1 (
        echo [环境] 官方源失败, 尝试清华镜像源...
        "%RTPY%" -m pip install --quiet -i https://pypi.tuna.tsinghua.edu.cn/simple -r patcher\requirements.txt
        if errorlevel 1 (
            echo [错误] 依赖安装失败, 请检查网络后重试
            pause
            exit /b 1
        )
    )
    echo ok> ".venv\Scripts\.deps_ok"
)

rem ---- 3. 执行汉化并启动游戏 ----
"%RTPY%" patcher\install_mod.py %*
if errorlevel 1 (
    echo.
    echo [结束] 汉化未完成, 请根据上面的提示处理后再试。
    pause
    exit /b 1
)

endlocal
exit /b 0
'''

out = Path(r"C:\Users\fanchengpeng\.zcode\workspace\default\rogue-tower-cn\一键汉化启动.bat")
out.write_bytes(CONTENT.replace("\r\n", "\n").replace("\n", "\r\n").encode("gbk"))
print("written GBK bat,", out.stat().st_size, "bytes")
