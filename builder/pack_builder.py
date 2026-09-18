# -*- coding: utf-8 -*-
"""
安装包制作器 —— 一键生成 setup.exe 安装包（Google Material 风格）
用法: python pack_builder.py
"""
import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import builder_core

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
WIN_W, WIN_H = 660, 700


class MaterialButton(tk.Canvas):
    def __init__(self, master, text, command, primary=True, width=0, height=44,
                 font_size=13, bg=BG):
        super().__init__(master, width=width, height=height, highlightthickness=0, bg=bg)
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


class MaterialEntry(tk.Entry):
    def __init__(self, master, **kw):
        super().__init__(master, font=(FONT, 10), relief="solid", bd=1,
                         highlightthickness=1, highlightcolor=GOOGLE_BLUE,
                         highlightbackground=BORDER, fg=TEXT_DARK, bg=BG, **kw)


class Card(tk.Frame):
    def __init__(self, master, title=None):
        super().__init__(master, bg=BG, highlightbackground=BORDER,
                         highlightthickness=1, bd=0)
        self.pack(fill="x", pady=(0, 12))
        inner = tk.Frame(self, bg=BG)
        inner.pack(fill="both", expand=True, padx=20, pady=16)
        self.inner = inner
        if title:
            tk.Label(inner, text=title, font=(FONT, 12, "bold"), bg=BG,
                     fg=TEXT_DARK).pack(anchor="w", pady=(0, 10))


class ScrollableFrame(tk.Frame):
    """可滚动容器，用于小屏适配"""
    def __init__(self, master):
        super().__init__(master, bg=BG)
        self.canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=BG)
        self.inner.bind("<Configure>",
                        lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.win, width=e.width))
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.vsb.pack(side="right", fill="y")
        self.canvas.bind_all("<MouseWheel>", self._wheel)

    def _wheel(self, e):
        if self.winfo_ismapped():
            self.canvas.yview_scroll(int(-e.delta / 120), "units")

    def scroll_top(self):
        self.canvas.yview_moveto(0)


class PackBuilderApp:
    def __init__(self, root):
        self.root = root
        root.title("安装包制作器")
        root.configure(bg=BG)
        root.geometry("%dx%d" % (WIN_W, WIN_H))
        root.minsize(WIN_W, 700)
        self.var_name = tk.StringVar()
        self.var_version = tk.StringVar(value="1.0.0")
        self.var_publisher = tk.StringVar()
        self.var_exe = tk.StringVar()
        self.var_outdir = tk.StringVar()
        self.var_icon = tk.StringVar()
        self.var_desktop = tk.BooleanVar(value=True)
        self.var_startmenu = tk.BooleanVar(value=True)
        self.var_autostart = tk.BooleanVar(value=True)
        self.extra_items = []
        self.building = False
        self._build_ui()
        self._set_default_icon()

    # ---------- UI ----------
    def _build_ui(self):
        outer = tk.Frame(self.root, bg=BG)
        outer.pack(fill="both", expand=True)

        # 顶部
        header = tk.Frame(outer, bg=BG)
        header.pack(fill="x", padx=36, pady=(28, 8))
        tk.Label(header, text="安装包制作器", font=(FONT, 24, "bold"), bg=BG,
                 fg=TEXT_DARK).pack(side="left")
        tk.Label(header, text="选择主程序，一键生成带快捷方式、自启与卸载功能的安装包",
                 font=(FONT, 10), bg=BG, fg=TEXT_GRAY).pack(side="right", pady=(8, 0))

        scroll = ScrollableFrame(outer)
        scroll.pack(fill="both", expand=True, padx=36)
        body = scroll.inner

        # 卡片1 应用信息
        c1 = Card(body, "应用信息")
        g1 = tk.Frame(c1.inner, bg=BG)
        g1.pack(fill="x")
        for i, (label, var, ph) in enumerate([
            ("应用名称", self.var_name, "例如：我的软件"),
            ("版本号", self.var_version, "1.0.0"),
            ("公司/作者", self.var_publisher, "可选")]):
            tk.Label(g1, text=label, font=(FONT, 10), bg=BG, fg=TEXT_GRAY).grid(
                row=i, column=0, sticky="w", pady=5, padx=(0, 12))
            MaterialEntry(g1, textvariable=var).grid(row=i, column=1, sticky="ew",
                                                     pady=5, ipady=6)
        g1.columnconfigure(1, weight=1)

        # 卡片2 主程序与附加文件
        c2 = Card(body, "主程序")
        row2 = tk.Frame(c2.inner, bg=BG)
        row2.pack(fill="x")
        MaterialEntry(row2, textvariable=self.var_exe).pack(side="left", fill="x",
                                                            expand=True, ipady=6)
        MaterialButton(row2, "选择主程序", self._pick_exe, width=110,
                       height=36, font_size=12).pack(side="left", padx=(8, 0))
        tk.Label(c2.inner, text="主程序将安装到目标目录并作为快捷方式指向的程序（支持 .exe）。",
                 font=(FONT, 9), bg=BG, fg=TEXT_GRAY).pack(anchor="w", pady=(6, 4))

        extra_header = tk.Frame(c2.inner, bg=BG)
        extra_header.pack(fill="x", pady=(8, 0))
        tk.Label(extra_header, text="附加文件 / 文件夹（可选，随主程序一起安装）",
                 font=(FONT, 10), bg=BG, fg=TEXT_GRAY).pack(side="left")
        MaterialButton(extra_header, "添加", self._add_extra, primary=False,
                       width=64, height=28, font_size=10).pack(side="right")
        MaterialButton(extra_header, "删除选中", self._remove_extra, primary=False,
                       width=84, height=28, font_size=10).pack(side="right", padx=(0, 6))

        lf = tk.Frame(c2.inner, bg=BG, highlightbackground=BORDER, highlightthickness=1)
        lf.pack(fill="x", pady=(6, 0))
        self.extra_list = tk.Listbox(lf, height=4, font=(FONT, 9), bg=BG, fg=TEXT_DARK,
                                     selectbackground=BLUE_LIGHT, selectforeground=TEXT_DARK,
                                     relief="flat", highlightthickness=0, activestyle="none")
        self.extra_list.pack(fill="x", padx=2, pady=2)

        # 卡片3 安装选项
        c3 = Card(body, "安装选项")
        for var, text in ((self.var_desktop, "在桌面创建快捷方式"),
                          (self.var_startmenu, "在开始菜单创建快捷方式"),
                          (self.var_autostart, "开机时自动启动主程序")):
            tk.Checkbutton(c3.inner, text=text, variable=var, bg=BG, fg=TEXT_DARK,
                           activebackground=BG, selectcolor=BG, font=(FONT, 11),
                           anchor="w", highlightthickness=0, bd=0).pack(fill="x", pady=3)

        # 卡片4 图标与输出
        c4 = Card(body, "图标与输出")
        row4a = tk.Frame(c4.inner, bg=BG)
        row4a.pack(fill="x")
        self.icon_preview = tk.Label(row4a, bg=BG, width=40, height=40)
        self.icon_preview.pack(side="left")
        col = tk.Frame(row4a, bg=BG)
        col.pack(side="left", fill="x", expand=True, padx=(10, 0))
        e1 = MaterialEntry(col, textvariable=self.var_icon)
        e1.pack(fill="x", ipady=6)
        tk.Label(col, text="留空则使用默认图标；支持 .ico / .png / .jpg",
                 font=(FONT, 9), bg=BG, fg=TEXT_GRAY).pack(anchor="w", pady=(4, 0))
        MaterialButton(row4a, "选择图标", self._pick_icon, primary=False, width=90,
                       height=36, font_size=12).pack(side="right", padx=(8, 0))

        row4b = tk.Frame(c4.inner, bg=BG)
        row4b.pack(fill="x", pady=(14, 0))
        MaterialEntry(row4b, textvariable=self.var_outdir).pack(side="left", fill="x",
                                                                expand=True, ipady=6)
        MaterialButton(row4b, "输出目录", self._pick_outdir, width=90, height=36,
                       font_size=12).pack(side="left", padx=(8, 0))
        tk.Label(c4.inner, text="生成的 setup.exe、uninstall.exe 与安装信息将保存到该目录。",
                 font=(FONT, 9), bg=BG, fg=TEXT_GRAY).pack(anchor="w", pady=(6, 0))

        # 日志卡片
        self.log_card = Card(body, "构建日志")
        self.log_text = tk.Text(self.log_card.inner, height=8, font=("Consolas", 9),
                                bg=BG_GRAY, fg=TEXT_DARK, relief="flat", wrap="word",
                                state="disabled")
        self.log_text.pack(fill="x")
        self.log_text.tag_configure("ok", foreground=GREEN)
        self.log_text.tag_configure("err", foreground="#D93025")

        # 底部操作
        bottom = tk.Frame(outer, bg=BG)
        bottom.pack(fill="x", padx=36, pady=(6, 22))
        self.progress = ttk.Progressbar(bottom, mode="indeterminate",
                                        style="Material.Horizontal.TProgressbar")
        self.btn_build = MaterialButton(bottom, "生成安装包", self._generate,
                                        width=220, height=52, font_size=15)
        self.btn_open = MaterialButton(bottom, "打开输出目录", self._open_outdir,
                                       primary=False, width=150, height=44)
        self.btn_open.pack(side="right")
        self.btn_build.pack(side="right", padx=(0, 12))
        self.progress.pack(fill="x", pady=(0, 14))

        try:
            style = ttk.Style()
            style.theme_use("clam")
            style.configure("Material.Horizontal.TProgressbar", troughcolor=BORDER,
                            background=GOOGLE_BLUE, bordercolor=BG, lightcolor=GOOGLE_BLUE,
                            darkcolor=GOOGLE_BLUE, thickness=5)
        except Exception:
            pass

    def _set_default_icon(self):
        try:
            import tempfile
            png = os.path.join(tempfile.gettempdir(), "pkg_default_icon.png")
            builder_core.make_default_icon(
                os.path.join(tempfile.gettempdir(), "pkg_default_icon.ico"), png)
            self._show_icon_preview(png)
            try:
                self.root.iconbitmap(os.path.join(tempfile.gettempdir(), "pkg_default_icon.ico"))
            except Exception:
                pass
        except Exception:
            pass

    def _show_icon_preview(self, path):
        try:
            from PIL import Image, ImageTk
            img = Image.open(path).convert("RGBA").resize((40, 40), Image.LANCZOS)
            self._icon_photo = ImageTk.PhotoImage(img)
            self.icon_preview.configure(image=self._icon_photo)
        except Exception:
            pass

    # ---------- 交互 ----------
    def _pick_exe(self):
        f = filedialog.askopenfilename(
            title="选择主程序", filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")])
        if f:
            self.var_exe.set(f)
            if not self.var_outdir.get():
                self.var_outdir.set(os.path.join(os.path.dirname(f), "安装包"))

    def _add_extra(self):
        files = filedialog.askopenfilenames(title="添加附加文件")
        for f in files:
            if f not in self.extra_items:
                self.extra_items.append(f)
                self.extra_list.insert("end", f)
        d = filedialog.askdirectory(title="添加附加文件夹")
        if d:
            if d not in self.extra_items:
                self.extra_items.append(d)
                self.extra_list.insert("end", d + "  (文件夹)")

    def _remove_extra(self):
        sel = list(self.extra_list.curselection())
        for i in reversed(sel):
            self.extra_list.delete(i)
            del self.extra_items[i]

    def _pick_icon(self):
        f = filedialog.askopenfilename(
            title="选择图标", filetypes=[("图标/图片", "*.ico *.png *.jpg *.jpeg *.bmp")])
        if f:
            self.var_icon.set(f)
            self._show_icon_preview(f)

    def _pick_outdir(self):
        d = filedialog.askdirectory(title="选择输出目录",
                                    initialdir=self.var_outdir.get() or os.getcwd())
        if d:
            self.var_outdir.set(d)

    # ---------- 生成 ----------
    def _generate(self):
        if self.building:
            return
        name = self.var_name.get().strip()
        exe = self.var_exe.get().strip()
        outdir = self.var_outdir.get().strip()
        if not name:
            messagebox.showwarning("提示", "请填写应用名称")
            return
        if not exe or not os.path.exists(exe):
            messagebox.showwarning("提示", "请选择主程序文件")
            return
        if not outdir:
            messagebox.showwarning("提示", "请选择输出目录")
            return
        config = {
            "app_name": name,
            "version": self.var_version.get().strip() or "1.0.0",
            "publisher": self.var_publisher.get().strip(),
            "exe_path": exe,
            "extra_items": list(self.extra_items),
            "autostart": self.var_autostart.get(),
            "desktop_shortcut": self.var_desktop.get(),
            "startmenu_shortcut": self.var_startmenu.get(),
            "icon_path": self.var_icon.get().strip() or None,
        }
        self.building = True
        self.btn_build.configure(state="disabled")
        self.btn_build.text = "正在生成…"
        self.btn_build._draw()
        self.progress.start(12)
        self._log("开始生成安装包：%s\n" % name)
        threading.Thread(target=self._build_worker, args=(config, outdir),
                         daemon=True).start()

    def _build_worker(self, config, outdir):
        try:
            setup, uninst, info = builder_core.build_installer(config, outdir, log=self._log)
            self._log("\n[完成] setup.exe 已生成：" + setup + "\n", tag="ok")
            self.root.after(0, self._done, True, setup)
        except Exception as e:
            self._log("\n[错误] " + str(e) + "\n", tag="err")
            self.root.after(0, self._done, False, None)

    def _done(self, ok, path):
        self.building = False
        self.progress.stop()
        self.btn_build.configure(state="normal")
        self.btn_build.text = "生成安装包"
        self.btn_build._draw()
        if ok:
            messagebox.showinfo("完成", "安装包生成完成！\n%s" % path)
            self._open_outdir()
        else:
            messagebox.showerror("失败", "安装包生成失败，请查看构建日志。")

    def _log(self, msg, tag=None):
        def upd():
            self.log_text.configure(state="normal")
            self.log_text.insert("end", msg, tag)
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        try:
            self.root.after(0, upd)
        except Exception:
            pass

    def _open_outdir(self):
        d = self.var_outdir.get().strip()
        if d and os.path.isdir(d):
            os.startfile(d)
        else:
            messagebox.showinfo("提示", "请先生成安装包。")


def main():
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    root = tk.Tk()
    root.configure(bg=BG)
    PackBuilderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
