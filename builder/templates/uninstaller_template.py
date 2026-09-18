# -*- coding: utf-8 -*-
"""
卸载器模板 —— 由「安装包制作器」渲染后经 PyInstaller 打包为 uninstall.exe
占位符: __APP_NAME__ __EXE_NAME__ __APP_KEY__ __HAS_ICON__
"""
import os
import sys
import shutil
import subprocess
import tempfile
import winreg
import ctypes
import tkinter as tk

APP_NAME = "__APP_NAME__"
EXE_NAME = "__EXE_NAME__"
APP_KEY = "__APP_KEY__"
HAS_ICON = "__HAS_ICON__" == "1"

GOOGLE_BLUE = "#1A73E8"
BLUE_HOVER = "#1765CC"
BLUE_LIGHT = "#E8F0FE"
BG = "#FFFFFF"
TEXT_DARK = "#202124"
TEXT_GRAY = "#5F6368"
BORDER = "#DADCE0"
RED = "#D93025"
FONT = "Segoe UI"
SILENT = "--silent" in sys.argv


def ps_str(s):
    return "'" + str(s).replace("'", "''") + "'"


def get_desktop():
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


def remove_shortcut(path):
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


def remove_autostart():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Run", 0,
                             winreg.KEY_SET_VALUE)
        try:
            winreg.DeleteValue(key, APP_NAME)
        except FileNotFoundError:
            pass
        winreg.CloseKey(key)
    except Exception:
        pass


def remove_uninstall_registry():
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER,
                         r"Software\Microsoft\Windows\CurrentVersion\Uninstall\%s" % APP_KEY)
    except Exception:
        pass


def cleanup(install_dir):
    remove_shortcut(os.path.join(get_desktop(), APP_NAME + ".lnk"))
    remove_shortcut(os.path.join(get_start_menu(), APP_NAME + ".lnk"))
    remove_autostart()
    remove_uninstall_registry()
    return install_dir


def delete_tree_later(install_dir):
    """复制自身到临时目录，由副本执行目录删除，规避文件占用。"""
    try:
        me = sys.executable
        tmp = os.path.join(tempfile.gettempdir(),
                           "uninstall_%s_%d.exe" % (APP_KEY, os.getpid()))
        shutil.copy2(me, tmp)
        subprocess.Popen([tmp, "--post-delete", install_dir], creationflags=0x08000000)
    except Exception:
        # 兜底：直接尝试删除（可能因占用失败，尽力而为）
        try:
            shutil.rmtree(install_dir, ignore_errors=True)
        except Exception:
            pass


def post_delete(install_dir):
    for _ in range(50):
        try:
            shutil.rmtree(install_dir)
            break
        except Exception:
            import time
            time.sleep(0.2)
    try:
        os.remove(sys.executable)
    except Exception:
        pass


# ============ Google 风格组件 ============
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
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.bind("<Button-1>", lambda e: self.command())
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
        for x, y in ((0, 0), (w - r * 2, 0), (0, h - r * 2), (w - r * 2, h - r * 2)):
            self.create_oval(x, y, x + r * 2, y + r * 2, fill=fill, outline=outline)
        self.create_rectangle(r, 0, w - r, h, fill=fill, outline=outline)
        self.create_rectangle(0, r, w, h - r, fill=fill, outline=outline)
        fg = "#FFFFFF" if self.primary else TEXT_DARK
        self.create_text(w // 2, h // 2, text=self.text, font=self.font, fill=fg)

    def _enter(self, _):
        self.hover = True
        self._draw()

    def _leave(self, _):
        self.hover = False
        self._draw()


class UninstallDialog:
    def __init__(self, root, install_dir):
        self.root = root
        self.install_dir = install_dir
        root.title("卸载 " + APP_NAME)
        root.configure(bg=BG)
        root.resizable(False, False)
        w, h = 460, 320
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry("%dx%d+%d+%d" % (w, h, (sw - w) // 2, (sh - h) // 2))
        self.build()

    def build(self):
        for c in self.root.winfo_children():
            c.destroy()
        p = tk.Frame(self.root, bg=BG)
        p.pack(fill="both", expand=True, padx=40, pady=36)
        tk.Label(p, text="卸载 %s" % APP_NAME, font=(FONT, 20, "bold"), bg=BG,
                 fg=TEXT_DARK).pack(anchor="w")
        tk.Label(p,
                 text="将删除 %s 的程序文件、快捷方式和开机自启项。\n此操作不可撤销，确定要继续吗？" % APP_NAME,
                 font=(FONT, 11), bg=BG, fg=TEXT_GRAY, justify="left").pack(anchor="w", pady=(14, 28))
        btns = tk.Frame(p, bg=BG)
        btns.pack(fill="x")
        MaterialButton(btns, "取消", self.root.destroy, primary=False, width=96).pack(side="left")
        MaterialButton(btns, "卸载", self.do_uninstall, width=120).pack(side="right")

    def do_uninstall(self):
        for c in self.root.winfo_children():
            c.destroy()
        p = tk.Frame(self.root, bg=BG)
        p.pack(fill="both", expand=True, padx=40, pady=36)
        tk.Label(p, text="正在卸载…", font=(FONT, 20, "bold"), bg=BG, fg=TEXT_DARK).pack(anchor="w")
        tk.Label(p, text="正在清理快捷方式、自启项和注册信息。",
                 font=(FONT, 11), bg=BG, fg=TEXT_GRAY).pack(anchor="w", pady=(12, 16))
        prog = tk.ttk.Progressbar(p, maximum=1.0, value=0.4, style="M.Horizontal.TProgressbar")
        prog.pack(fill="x")
        p.update_idletasks()
        try:
            target = cleanup(self.install_dir)
            delete_tree_later(target)
            prog["value"] = 1.0
            p.update_idletasks()
            for c in self.root.winfo_children():
                c.destroy()
            p2 = tk.Frame(self.root, bg=BG)
            p2.pack(fill="both", expand=True, padx=40, pady=36)
            tk.Label(p2, text="卸载完成", font=(FONT, 22, "bold"), bg=BG, fg="#188038").pack(anchor="w")
            tk.Label(p2, text="%s 已从你的电脑中移除。" % APP_NAME, font=(FONT, 11),
                     bg=BG, fg=TEXT_DARK).pack(anchor="w", pady=(12, 24))
            MaterialButton(p2, "关闭", self.root.destroy, width=96).pack(anchor="w")
        except Exception as e:
            for c in self.root.winfo_children():
                c.destroy()
            p3 = tk.Frame(self.root, bg=BG)
            p3.pack(fill="both", expand=True, padx=40, pady=36)
            tk.Label(p3, text="卸载失败", font=(FONT, 22, "bold"), bg=BG, fg=RED).pack(anchor="w")
            tk.Label(p3, text=str(e), font=(FONT, 10), bg=BG, fg=TEXT_GRAY,
                     wraplength=360, justify="left").pack(anchor="w", pady=(12, 20))
            MaterialButton(p3, "关闭", self.root.destroy, primary=False, width=96).pack(anchor="w")


def main():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    if "--post-delete" in sys.argv:
        idx = sys.argv.index("--post-delete")
        if idx + 1 < len(sys.argv):
            post_delete(sys.argv[idx + 1])
        return
    if SILENT:
        cleanup(os.path.dirname(os.path.abspath(sys.argv[0])))
        delete_tree_later(os.path.dirname(os.path.abspath(sys.argv[0])))
        return
    try:
        style = tk.ttk.Style()
        style.theme_use("clam")
        style.configure("M.Horizontal.TProgressbar", troughcolor=BORDER,
                        background=GOOGLE_BLUE, bordercolor=BG,
                        lightcolor=GOOGLE_BLUE, darkcolor=GOOGLE_BLUE, thickness=6)
    except Exception:
        pass
    root = tk.Tk()
    root.configure(bg=BG)
    if HAS_ICON and os.path.exists(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "app.ico")):
        try:
            root.iconbitmap(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "app.ico"))
        except Exception:
            pass
    install_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    UninstallDialog(root, install_dir)
    root.mainloop()


if __name__ == "__main__":
    main()
