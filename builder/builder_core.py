# -*- coding: utf-8 -*-
"""安装包制作器 —— 打包核心：模板渲染 / 图标生成 / PyInstaller 构建"""
import os
import sys
import json
import shutil
import subprocess
import tempfile

_PY_CACHE = None


def _has_pyinstaller(py):
    try:
        r = subprocess.run([py, "-c", "import PyInstaller"],
                           capture_output=True, timeout=30,
                           creationflags=0x08000000)
        return r.returncode == 0
    except Exception:
        return False


def find_python_with_pyinstaller():
    """探测装有 PyInstaller 的 Python 解释器（依次：当前解释器 → py 启动器 → PATH）"""
    global _PY_CACHE
    if _PY_CACHE:
        return _PY_CACHE
    # 打包成 exe 时 sys.executable 是程序自身，不能作为候选解释器
    cands = [] if getattr(sys, "frozen", False) else [sys.executable]
    try:
        r = subprocess.run(["py", "-0p"], capture_output=True, text=True, timeout=15,
                           creationflags=0x08000000)
        for line in (r.stdout or "").splitlines():
            if "python.exe" in line:
                p = line.split()[-1].strip().strip("*")
                if p and p not in cands:
                    cands.append(p)
    except Exception:
        pass
    # PATH 中所有 python 解释器
    for name in ("python.exe", "python3.exe", "pythonw.exe"):
        for d in os.environ.get("PATH", "").split(os.pathsep):
            if not d:
                continue
            p = os.path.join(d.strip('"'), name)
            if os.path.isfile(p) and p not in cands:
                cands.append(p)
    for p in cands:
        if p and os.path.exists(p) and _has_pyinstaller(p):
            _PY_CACHE = p
            return p
    return None

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

PLACEHOLDERS = [
    "__APP_NAME__", "__APP_VERSION__", "__PUBLISHER__", "__EXE_NAME__", "__APP_KEY__",
    "__AUTOSTART_DEFAULT__", "__DESKTOP_DEFAULT__", "__STARTMENU_DEFAULT__", "__HAS_ICON__",
]


def app_key(app_name, publisher):
    """注册表键：只保留字母数字，避免特殊字符问题"""
    s = (publisher + "_" + app_name).strip()
    return "".join(c for c in s if c.isalnum() or c in "-_.") or "InstalledApp"


def render_template(template_path, config, out_path):
    with open(template_path, "r", encoding="utf-8") as f:
        text = f.read()
    repl = {
        "__APP_NAME__": config["app_name"],
        "__APP_VERSION__": config["version"],
        "__PUBLISHER__": config["publisher"],
        "__EXE_NAME__": config["exe_name"],
        "__APP_KEY__": config["app_key"],
        "__AUTOSTART_DEFAULT__": "1" if config["autostart"] else "0",
        "__DESKTOP_DEFAULT__": "1" if config["desktop_shortcut"] else "0",
        "__STARTMENU_DEFAULT__": "1" if config["startmenu_shortcut"] else "0",
        "__HAS_ICON__": "1" if config.get("has_icon") else "0",
    }
    for k, v in repl.items():
        text = text.replace(k, v)
    # 兜底：确保没有未替换的占位符残留
    for ph in PLACEHOLDERS:
        if ph in text:
            text = text.replace(ph, "App")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)
    return out_path


DEFAULT_ICO = os.path.join(ASSET_DIR, "default.ico")
DEFAULT_PNG = os.path.join(ASSET_DIR, "default.png")


def make_default_icon(out_ico_path, out_png_path=None):
    """默认图标：优先使用预生成资源，PIL 仅在资源缺失时兜底"""
    out_ico_path = os.path.abspath(out_ico_path)
    os.makedirs(os.path.dirname(out_ico_path), exist_ok=True)
    if os.path.exists(DEFAULT_ICO):
        shutil.copy2(DEFAULT_ICO, out_ico_path)
        if out_png_path and os.path.exists(DEFAULT_PNG):
            shutil.copy2(DEFAULT_PNG, os.path.abspath(out_png_path))
        return out_ico_path
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return None
    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # 蓝色圆角底
    d.rounded_rectangle([8, 8, size - 8, size - 8], radius=56, fill=(26, 115, 232, 255))
    white = (255, 255, 255, 255)
    # 底部托盘（盒子）
    d.rounded_rectangle([72, 168, 184, 196], radius=8, fill=white)
    # 盒子左右壁
    d.rectangle([72, 120, 88, 196], fill=white)
    d.rectangle([168, 120, 184, 196], fill=white)
    # 向下箭头
    d.rectangle([120, 56, 136, 140], fill=white)
    d.polygon([(84, 96), (172, 96), (128, 148)], fill=white)
    # 顶部横盖
    d.rounded_rectangle([64, 96, 192, 108], radius=6, fill=white)
    out_ico_path = os.path.abspath(out_ico_path)
    os.makedirs(os.path.dirname(out_ico_path), exist_ok=True)
    img.save(out_ico_path, format="ICO", sizes=[(16, 16), (24, 24), (32, 32),
                                                (48, 48), (64, 64), (128, 128), (256, 256)])
    if out_png_path:
        img.save(out_png_path, format="PNG")
    return out_ico_path


def copy_app_payload(exe_path, extra_items, work_dir):
    """把主程序与附加内容复制到构建用的 app 目录，返回 (app_dir, add_data_list, total_bytes)"""
    app_dir = os.path.join(work_dir, "payload", "app")
    os.makedirs(app_dir, exist_ok=True)
    add_data = []
    total = 0
    # 主程序
    if exe_path and os.path.exists(exe_path):
        target = os.path.join(app_dir, os.path.basename(exe_path))
        shutil.copy2(exe_path, target)
        add_data.append("%s;app" % target)
        total += os.path.getsize(target)
    # 附加文件/目录
    for item in extra_items or []:
        if not item or not os.path.exists(item):
            continue
        name = os.path.basename(os.path.normpath(item))
        dst = os.path.join(app_dir, name)
        if os.path.isdir(item):
            shutil.copytree(item, dst, dirs_exist_ok=True)
            for root, _dirs, files in os.walk(dst):
                for fn in files:
                    total += os.path.getsize(os.path.join(root, fn))
        else:
            shutil.copy2(item, dst)
            total += os.path.getsize(dst)
        add_data.append("%s;app" % dst)
    return app_dir, add_data, total


def run_pyinstaller(script, out_dir, work_dir, name, icon_ico, add_data=None, log=None):
    """调用 PyInstaller 打包单个 exe"""
    py = find_python_with_pyinstaller()
    if not py:
        raise RuntimeError(
            "未找到可用的 PyInstaller。\n"
            "请在命令行执行：pip install pyinstaller\n"
            "然后重新生成安装包。")
    cmd = [py, "-m", "PyInstaller",
           "--noconfirm", "--clean", "--onefile", "--noconsole",
           "--name", name,
           "--distpath", out_dir,
           "--workpath", os.path.join(work_dir, "work_" + name),
           "--specpath", os.path.join(work_dir, "spec_" + name)]
    if icon_ico and os.path.exists(icon_ico):
        cmd += ["--icon", icon_ico]
    for d in add_data or []:
        cmd += ["--add-data", d]
    cmd.append(script)
    env = dict(os.environ)
    if log:
        log("[构建] " + " ".join(cmd) + "\n")
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env,
                          creationflags=0x08000000, encoding="utf-8", errors="replace")
    if log:
        tail = (proc.stdout + proc.stderr)[-4000:]
        log(tail + "\n")
    if proc.returncode != 0:
        raise RuntimeError("PyInstaller 构建 %s 失败，详见上方日志。" % name)
    return os.path.join(out_dir, name + ".exe")


def build_python_main(config, icon_ico, work_dir, log=None):
    """Python 入口脚本 → PyInstaller 壳（单文件 exe），供安装包作为主程序使用。

    附加文件/文件夹通过 --add-data 内嵌进主程序（运行时位于 sys._MEIPASS）。
    """
    py = find_python_with_pyinstaller()
    if not py:
        raise RuntimeError(
            "未找到可用的 PyInstaller。\n"
            "请在命令行执行：pip install pyinstaller\n"
            "然后重新生成安装包。")
    entry = config["python_entry"]
    name = config["app_name"].strip()
    out = os.path.join(work_dir, "python_main")
    os.makedirs(out, exist_ok=True)
    cmd = [py, "-m", "PyInstaller",
           "--noconfirm", "--clean", "--onefile", "--windowed",
           "--name", name,
           "--distpath", out,
           "--workpath", os.path.join(work_dir, "work_pymain"),
           "--specpath", os.path.join(work_dir, "spec_pymain")]
    if icon_ico and os.path.exists(icon_ico):
        cmd += ["--icon", icon_ico]
    for item in config.get("extra_items") or []:
        if os.path.exists(item):
            cmd += ["--add-data", "%s;." % item]
    cmd.append(entry)
    if log:
        log("[构建] " + " ".join(cmd) + "\n")
    proc = subprocess.run(cmd, capture_output=True, text=True, env=dict(os.environ),
                          creationflags=0x08000000, encoding="utf-8", errors="replace")
    if log:
        log((proc.stdout + proc.stderr)[-4000:] + "\n")
    if proc.returncode != 0:
        raise RuntimeError("PyInstaller 打包 Python 主程序失败，详见上方日志。")
    return os.path.join(out, name + ".exe")


def build_installer(config, out_dir, log=None):
    """
    config: {
      app_name, version, publisher, exe_path | python_entry,
      extra_items: [], autostart, desktop_shortcut, startmenu_shortcut, icon_path
    }
    支持两种主程序来源：
      - exe_path:     现成可执行文件（.exe）
      - python_entry: Python 入口脚本（.py/.pyw），自动经 PyInstaller 打包为 exe 再制作安装包
    产出: out_dir/setup_<name>.exe 与 out_dir/uninstall.exe
    """
    app_name = config["app_name"].strip()
    if not app_name:
        raise ValueError("应用名称不能为空")
    python_entry = config.get("python_entry")
    exe_path = config.get("exe_path")
    if python_entry:
        if not os.path.exists(python_entry):
            raise ValueError("Python 入口脚本不存在，请重新选择")
    elif exe_path and os.path.exists(exe_path):
        if not os.path.splitext(exe_path)[1].lower() in (".exe", ".bat", ".cmd", ".com", ".lnk"):
            raise ValueError("主程序应为可执行文件（.exe）")
    else:
        raise ValueError("请选择主程序文件（.exe）或 Python 入口脚本（.py）")

    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)

    # 构建工作目录（临时）
    work_dir = tempfile.mkdtemp(prefix="pkgbuild_")
    try:
        cfg = dict(config)
        cfg["app_key"] = app_key(app_name, config.get("publisher", ""))
        cfg["has_icon"] = bool(config.get("icon_path") and os.path.exists(config["icon_path"]))
        cfg.setdefault("version", "1.0.0")
        cfg.setdefault("publisher", "")

        # 图标
        if cfg["has_icon"]:
            icon_ico = os.path.abspath(cfg["icon_path"])
            if not icon_ico.lower().endswith(".ico"):
                try:
                    from PIL import Image
                except ImportError:
                    raise RuntimeError(
                        "当前 Python 环境缺少 Pillow，无法将 %s 转换为 .ico。\n"
                        "请使用 .ico 图标文件，或运行：pip install pillow" %
                        os.path.splitext(icon_ico)[1])
                img = Image.open(icon_ico).convert("RGBA")
                icon_ico = os.path.join(work_dir, "icon.ico")
                img.save(icon_ico, format="ICO", sizes=[(16, 16), (32, 32), (48, 48),
                                                        (64, 64), (128, 128), (256, 256)])
        else:
            icon_ico = os.path.join(work_dir, "icon.ico")
            if not make_default_icon(icon_ico):
                raise RuntimeError("默认图标生成失败：缺少 Pillow 且资源文件不可用。")

        # Python 模式：先用 PyInstaller 把入口脚本打成 exe（壳）
        if python_entry:
            if log:
                log("== PyInstaller 打包 Python 主程序（壳）==\n")
            exe_path = build_python_main(cfg, icon_ico, work_dir, log)
            cfg["exe_name"] = os.path.basename(exe_path)
            # 附加文件已内嵌进主程序，不再随安装包单独携带
            cfg["extra_items"] = []
        else:
            cfg["exe_name"] = os.path.basename(exe_path)

        # 复制应用负载
        app_dir, add_data, total_bytes = copy_app_payload(exe_path, cfg.get("extra_items"), work_dir)
        if log:
            log("负载大小：%.1f MB\n" % (total_bytes / 1048576.0))

        # 渲染安装器/卸载器源码
        installer_main = os.path.join(work_dir, "installer_main.py")
        uninstaller_main = os.path.join(work_dir, "uninstaller_main.py")
        render_template(os.path.join(TEMPLATE_DIR, "installer_template.py"), cfg, installer_main)
        render_template(os.path.join(TEMPLATE_DIR, "uninstaller_template.py"), cfg, uninstaller_main)

        # 1) 先构建卸载器
        if log:
            log("== 构建卸载程序 uninstall.exe ==\n")
        uninstall_exe = run_pyinstaller(uninstaller_main, out_dir, work_dir, "uninstall",
                                        icon_ico, None, log)

        # 2) 构建安装器（携带 app 负载 + uninstall.exe + 图标）
        if log:
            log("== 构建安装程序 setup.exe ==\n")
        setup_add = list(add_data)
        setup_add.append("%s;." % uninstall_exe)
        setup_add.append("%s;." % icon_ico)
        setup_name = "setup" if len(app_name) > 20 else "setup_" + app_name
        setup_exe = run_pyinstaller(installer_main, out_dir, work_dir, setup_name,
                                    icon_ico, setup_add, log)

        # 3) 生成安装信息文件
        info = {
            "app_name": app_name,
            "version": cfg["version"],
            "publisher": cfg["publisher"],
            "setup_exe": os.path.basename(setup_exe),
            "uninstall_exe": os.path.basename(uninstall_exe),
            "install_size_mb": round(total_bytes / 1048576.0, 1),
            "built_at": __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        info_path = os.path.join(out_dir, "安装信息.json")
        with open(info_path, "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)
        return setup_exe, uninstall_exe, info
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


if __name__ == "__main__":
    # 命令行模式：python builder_core.py <config.json> <out_dir>
    if len(sys.argv) >= 3:
        with open(sys.argv[1], "r", encoding="utf-8-sig") as f:
            cfg = json.load(f)
        s, u, i = build_installer(cfg, sys.argv[2], log=lambda m: print(m, end=""))
        print("DONE", s)
    else:
        print("usage: python builder_core.py config.json out_dir")
