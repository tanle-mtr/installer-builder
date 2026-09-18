@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo  将「安装包制作器」打包为独立 exe 程序
echo  产物: ..\dist\安装包制作器.exe
echo ============================================
where python >nul 2>nul
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.9+ 并勾选 "Add to PATH"
    pause
    exit /b 1
)
python build_gui.py
pause
