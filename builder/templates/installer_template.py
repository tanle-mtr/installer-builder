# -*- coding: utf-8 -*-
"""
安装器模板 —— 由「安装包制作器」渲染后经 PyInstaller 打包为 setup.exe
占位符: __APP_NAME__ __APP_VERSION__ __PUBLISHER__ __EXE_NAME__ __APP_KEY__
        __AUTOSTART_DEFAULT__ __DESKTOP_DEFAULT__ __STARTMENU_DEFAULT__ __HAS_ICON__
"""
import os
import sys
import json
import shutil
import subprocess
import winreg
import ctypes
import threading
import tkinter as tk
from tkinter import ttk, filedialog

# ============ 由生成器写入的配置 ============
APP_NAME = "__APP_NAME__"
APP_VERSION = "__APP_VERSION__"
PUBLISHER = "__PUBLISHER__"
EXE_NAME = "__EXE_NAME__"
APP_KEY = "__APP_KEY__"
AUTOSTART_DEFAULT = "__AUTOSTART_DEFAULT__" == "1"
DESKTOP_DEFAULT = "__DESKTOP_DEFAULT__" == "1"
STARTMENU_DEFAULT = "__STARTMENU_DEFAULT__" == "1"
HAS_ICON = "__HAS_ICON__" == "1"

GOOGLE_BLUE = "#1A73E8"
BLUE_HOVER = "#1765CC"
BLUE_LIGHT = "#E8F0FE"
BG = "#FFFFFF"
BG_GRAY = "#F8F9FA"
TEXT_DARK = "#202124"
TEXT_GRAY = "#5F6368"
BORDER = "#DADCE0"
GREEN = "#188038"
FONT = "Segoe UI"
SILENT = "--silent" in sys.argv or "/S" in [a.upper() for a in sys.argv]


def resource_path(rel):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


def ps_str(s):
    return "'" + str(s).replace("'", "''") + "'"


def create_shortcut(target, lnk_path, icon_path=None):
    try:
        if not target or not lnk_path:
            return False
        wd = os.path.dirname(target)
        icon = icon_path or target
        ps = ("$sh=New-Object -ComObject WScript.Shell;"
              "$s=$sh.CreateShortcut(" + ps_str(lnk_path) + ");"
              "$s.TargetPath=" + ps_str(target) + ";"
              "$s.WorkingDirectory=" + ps_str(wd) + ";"
              "$s.IconLocation=" + ps_str(icon) + ",0;"
              "$s.Save()")
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                           capture_output=True, text=True, creationflags=0x08000000)
        return r.returncode == 0
    except Exception:
        return False


def remove_shortcut(lnk_path):
    try:
        if os.path.exists(lnk_path):
            os.remove(lnk_path)
    except Exception:
        pass


def set_autostart(enable):
    try:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                               r"Software\Microsoft\Windows\CurrentVersion\Run")
        name = APP_NAME
        if enable:
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, '"%s"' % os.path.join(INSTALL_DIR, EXE_NAME))
        else:
            try:
                winreg.DeleteValue(key, name)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def write_uninstall_registry(install_dir):
    try:
        sub_key = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\%s" % APP_KEY
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, sub_key)
        uninst = os.path.join(install_dir, "uninstall.exe")
        icon = os.path.join(install_dir, EXE_NAME)
        values = {
            "DisplayName": APP_NAME,
            "DisplayVersion": APP_VERSION,
            "Publisher": PUBLISHER,
            "InstallLocation": install_dir,
            "DisplayIcon": icon,
            "UninstallString": '"%s"' % uninst,
            "QuietUninstallString": '"%s" --silent' % uninst,
            "NoModify": 1,
            "NoRepair": 1,
            "EstimatedSize": 0,
        }
        for k, v in values.items():
            if isinstance(v, int):
                winreg.SetValueEx(key, k, 0, winreg.REG_DWORD, v)
            else:
                winreg.SetValueEx(key, k, 0, winreg.REG_SZ, v)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def remove_uninstall_registry():
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER,
                         r"Software\Microsoft\Windows\CurrentVersion\Uninstall\%s" % APP_KEY)
    except Exception:
        pass


def get_desktop():
    import ctypes.wintypes
    try:
        buf = ctypes.create_unicode_buffer(260)
        ctypes.windll.shell32.SHGetFolderPathW(None, 0x0000, None, 0, buf)
        if buf.value:
            return buf.value
    except Exception:
        pass
    return os.path.join(os.path.expanduser("~"), "Desktop")


def get_start_menu():
    try:
        buf = ctypes.create_unicode_buffer(260)
        ctypes.windll.shell32.SHGetFolderPathW(None, 0x0002, None, 0, buf)
        if buf.value:
            return buf.value
    except Exception:
        pass
    return os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), r"Microsoft\Windows\Start Menu\Programs")


def default_install_dir():
    return os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "Programs", APP_NAME)


INSTALL_DIR = default_install_dir()

# ============ Google Material 风格组件 ============
class MaterialButton(tk.Canvas):
    def __init__(self, master, text, command, primary=True, width=0, height=44, font_size=13, **kw):
        tk.Canvas.__init__(self, master, width=width, height=height, highlightthickness=0,
                           bg=kw.pop("bg", BG))
        self.bg = kw.pop("bg", BG)
        self.text = text
        self.command = command
        self.primary = primary
        self.font = (FONT, font_size, "bold")
        self.hover = False
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        self.bind("<ButtonRelease-1>", self._on_release)
        self._draw()

    def _draw(self):
        self.delete("all")
        w = self.winfo_width() or 120
        h = self.winfo_height() or 44
        fill = BLUE_HOVER if (self.hover and self.primary) else GOOGLE_BLUE
        if not self.primary:
            fill = BLUE_LIGHT if self.hover else BG
        outline = "" if self.primary else BORDER
        r = 8
        self.create_oval(0, 0, r*2, r*2, fill=fill, outline=outline)
        self.create_oval(w-r*2, 0, w, r*2, fill=fill, outline=outline)
        self.create_oval(0, h-r*2, r*2, h, fill=fill, outline=outline)
        self.create_oval(w-r*2, h-r*2, w, h, fill=fill, outline=outline)
        self.create_rectangle(r, 0, w-r, h, fill=fill, outline=outline)
        self.create_rectangle(0, r, w, h-r, fill=fill, outline=outline)
        fg = "#FFFFFF" if self.primary else TEXT_DARK
        self.create_text(w//2, h//2, text=self.text, font=self.font, fill=fg)

    def _on_enter(self, _):
        self.hover = True
        self._draw()

    def _on_leave(self, _):
        self.hover = False
        self._draw()

    def _on_click(self, _):
        if self.command:
            self.command()

    def _on_release(self, _):
        pass


def make_card(parent, padx=0, pady=0):
    card = tk.Frame(parent, bg=BG, highlightbackground=BORDER, highlightthickness=1, bd=0)
    card.pack(fill="x", padx=padx, pady=pady)
    return card


# ============ 安装流程 ============
def do_install(install_dir, desktop_lnk, startmenu_lnk, autostart, on_step):
    steps = [
        ("正在准备安装目录…", lambda: os.makedirs(install_dir, exist_ok=True)),
        ("正在复制程序文件…", lambda: shutil.copytree(resource_path("app"), install_dir, dirs_exist_ok=True)),
        ("正在部署卸载程序…", lambda: shutil.copy2(resource_path("uninstall.exe"),
                                                os.path.join(install_dir, "uninstall.exe"))),
    ]
    if desktop_lnk:
        steps.append(("正在创建桌面快捷方式…", lambda: create_shortcut(
            os.path.join(install_dir, EXE_NAME), desktop_lnk,
            os.path.join(install_dir, "app.ico") if HAS_ICON else None)))
    if startmenu_lnk:
        steps.append(("正在创建开始菜单快捷方式…", lambda: create_shortcut(
            os.path.join(install_dir, EXE_NAME), startmenu_lnk,
            os.path.join(install_dir, "app.ico") if HAS_ICON else None)))
    steps += [
        ("正在设置开机自启…", lambda: set_autostart(autostart)),
        ("正在注册卸载信息…", lambda: write_uninstall_registry(install_dir)),
    ]
    for i, (label, fn) in enumerate(steps):
        on_step(label, (i + 1) / len(steps))
        try:
            fn()
        except Exception:
            raise
    on_step("安装完成", 1.0)


# ============ UI ============
class InstallerApp:
    def __init__(self, root):
        self.root = root
        root.title(APP_NAME + " 安装程序")
        root.configure(bg=BG)
        root.resizable(False, False)
        self.install_dir = tk.StringVar(value=default_install_dir())
        self.opt_desktop = tk.BooleanVar(value=DESKTOP_DEFAULT)
        self.opt_startmenu = tk.BooleanVar(value=STARTMENU_DEFAULT)
        self.opt_autostart = tk.BooleanVar(value=AUTOSTART_DEFAULT)
        self.page = None
        self.show_options()

    def clear(self):
        if self.page:
            self.page.destroy()

    def show_options(self):
        self.clear()
        p = tk.Frame(self.root, bg=BG)
        p.pack(fill="both", expand=True, padx=48, pady=32)
        tk.Label(p, text=APP_NAME, font=(FONT, 22, "bold"), bg=BG, fg=TEXT_DARK).pack(anchor="w")
        tk.Label(p, text="版本 %s  ·  由 %s 提供" % (APP_VERSION, PUBLISHER),
                 font=(FONT, 10), bg=BG, fg=TEXT_GRAY).pack(anchor="w", pady=(4, 20))

        card = make_card(p)
        inner = tk.Frame(card, bg=BG)
        inner.pack(fill="x", padx=20, pady=16)
        tk.Label(inner, text="安装位置", font=(FONT, 11, "bold"), bg=BG, fg=TEXT_DARK).pack(anchor="w")
        row = tk.Frame(inner, bg=BG)
        row.pack(fill="x", pady=(8, 4))
        entry = tk.Entry(row, textvariable=self.install_dir, font=(FONT, 10),
                         relief="solid", bd=1, highlightthickness=1, highlightcolor=GOOGLE_BLUE,
                         highlightbackground=BORDER, fg=TEXT_DARK, bg=BG)
        entry.pack(side="left", fill="x", expand=True, ipady=6)
        btn = MaterialButton(row, "浏览…", lambda: self._browse(), primary=False, width=86, height=36)
        btn.pack(side="left", padx=(8, 0))
        tk.Label(inner, text="程序将安装到该文件夹，可在“卸载或更改程序”中卸载。",
                 font=(FONT, 9), bg=BG, fg=TEXT_GRAY).pack(anchor="w", pady=(2, 10))

        for var, text in ((self.opt_desktop, "在桌面创建快捷方式"),
                          (self.opt_startmenu, "在开始菜单创建快捷方式"),
                          (self.opt_autostart, "开机时自动启动")):
            cb = tk.Checkbutton(inner, text=text, variable=var, bg=BG, fg=TEXT_DARK,
                                activebackground=BG, selectcolor=BG,
                                font=(FONT, 11), anchor="w",
                                highlightthickness=0, bd=0)
            cb.pack(fill="x", pady=4)

        btns = tk.Frame(p, bg=BG)
        btns.pack(fill="x", pady=(24, 0))
        MaterialButton(btns, "取消", self._cancel, primary=False, width=96).pack(side="left")
        MaterialButton(btns, "安装", self._start, width=128).pack(side="right")
        self.page = p

    def _browse(self):
        d = filedialog.askdirectory(title="选择安装位置", initialdir=self.install_dir.get())
        if d:
            self.install_dir.set(d)

    def _cancel(self):
        self.root.destroy()

    def _start(self):
        d = self.install_dir.get().strip()
        if not d or not os.path.isabs(d):
            return
        self.show_progress()
        threading.Thread(target=self._run_install, args=(d,), daemon=True).start()

    def show_progress(self):
        self.clear()
        p = tk.Frame(self.root, bg=BG)
        p.pack(fill="both", expand=True, padx=48, pady=40)
        tk.Label(p, text="正在安装 %s" % APP_NAME, font=(FONT, 20, "bold"),
                 bg=BG, fg=TEXT_DARK).pack(anchor="w")
        self.status_var = tk.StringVar(value="正在准备…")
        tk.Label(p, textvariable=self.status_var, font=(FONT, 11), bg=BG, fg=TEXT_GRAY).pack(anchor="w", pady=(12, 12))
        self.progress = ttk.Progressbar(p, maximum=1.0, value=0.0, style="Material.Horizontal.TProgressbar")
        self.progress.pack(fill="x")
        self.page = p

    def _run_install(self, d):
        desktop_lnk = os.path.join(get_desktop(), APP_NAME + ".lnk")
        startmenu_lnk = os.path.join(get_start_menu(), APP_NAME + ".lnk")
        try:
            do_install(d, desktop_lnk, startmenu_lnk, self.opt_autostart.get(),
                       lambda s, v: self._set_status(s, v))
            self.root.after(0, lambda: self.show_done(d))
        except Exception as e:
            self.root.after(0, lambda: self.show_error(str(e)))

    def _set_status(self, s, v):
        def upd():
            self.status_var.set(s)
            self.progress["value"] = v
            self.root.update_idletasks()
        self.root.after(0, upd)

    def show_done(self, d):
        self.clear()
        p = tk.Frame(self.root, bg=BG)
        p.pack(fill="both", expand=True, padx=48, pady=40)
        tk.Label(p, text="安装完成", font=(FONT, 24, "bold"), bg=BG, fg=GREEN).pack(anchor="w")
        tk.Label(p, text="%s 已成功安装。" % APP_NAME, font=(FONT, 12), bg=BG, fg=TEXT_DARK).pack(anchor="w", pady=(10, 24))
        btns = tk.Frame(p, bg=BG)
        btns.pack(fill="x")
        MaterialButton(btns, "关闭", self._cancel, primary=False, width=96).pack(side="left")
        MaterialButton(btns, "打开安装目录", lambda: (os.startfile(d), self._cancel()), width=148).pack(side="right", padx=(8, 0))
        MaterialButton(btns, "立即运行", lambda: (os.startfile(os.path.join(d, EXE_NAME)), self._cancel()),
                       width=120).pack(side="right")
        self.page = p

    def show_error(self, msg):
        self.clear()
        p = tk.Frame(self.root, bg=BG)
        p.pack(fill="both", expand=True, padx=48, pady=40)
        tk.Label(p, text="安装失败", font=(FONT, 22, "bold"), bg=BG, fg="#D93025").pack(anchor="w")
        tk.Label(p, text=msg, font=(FONT, 10), bg=BG, fg=TEXT_GRAY, wraplength=480,
                 justify="left").pack(anchor="w", pady=(12, 20))
        MaterialButton(p, "关闭", self._cancel, primary=False, width=96).pack(anchor="w")
        self.page = p


def run_silent():
    d = default_install_dir()
    try:
        do_install(d,
                   os.path.join(get_desktop(), APP_NAME + ".lnk") if DESKTOP_DEFAULT else "",
                   os.path.join(get_start_menu(), APP_NAME + ".lnk") if STARTMENU_DEFAULT else "",
                   AUTOSTART_DEFAULT, lambda s, v: None)
        print("OK:" + d)
    except Exception as e:
        print("ERR:" + str(e))
        sys.exit(1)


def main():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    if SILENT:
        run_silent()
        return
    try:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Material.Horizontal.TProgressbar", troughcolor=BORDER,
                        background=GOOGLE_BLUE, bordercolor=BG, lightcolor=GOOGLE_BLUE,
                        darkcolor=GOOGLE_BLUE, thickness=6)
    except Exception:
        pass
    root = tk.Tk()
    root.configure(bg=BG)
    w, h = 620, 520
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    root.geometry("%dx%d+%d+%d" % (w, h, (sw - w) // 2, (sh - h) // 2))
    if HAS_ICON and os.path.exists(resource_path("app.ico")):
        try:
            root.iconbitmap(resource_path("app.ico"))
        except Exception:
            pass
    InstallerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
