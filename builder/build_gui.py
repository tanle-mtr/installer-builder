# -*- coding: utf-8 -*-
"""把「安装包制作器」打包为独立 exe：python build_gui.py"""
import os
import sys
import subprocess

import builder_core

ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    py = builder_core.find_python_with_pyinstaller()
    if not py:
        print("[错误] 未找到带 PyInstaller 的 Python，请先运行: pip install pyinstaller")
        sys.exit(1)
    print("使用解释器:", py)
    cmd = [py, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile", "--windowed",
           "--name", "安装包制作器",
           "--add-data", os.path.join(ROOT, "templates") + ";templates",
           "--add-data", os.path.join(ROOT, "assets") + ";assets",
           os.path.join(ROOT, "pack_builder.py")]
    r = subprocess.run(cmd, cwd=ROOT)
    if r.returncode != 0:
        print("[错误] 打包失败，请查看上方日志")
        sys.exit(1)
    print("[完成] 已生成 %s" % os.path.join(ROOT, "dist", "安装包制作器.exe"))


if __name__ == "__main__":
    main()
