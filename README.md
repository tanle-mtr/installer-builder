# 安装包制作器 Installer Builder

> 一键制作 Windows 安装包：选择主程序，即可生成带 **桌面快捷方式、开机自启、卸载程序** 的 `setup.exe` 安装包。界面为 Google Material 风格。

参考 NSIS / Inno Setup 等开源安装器工具的功能集，使用 Python 标准库 + PyInstaller 实现，无需安装额外软件即可构建自己的安装包。

## 功能特性

- 🖱️ **选择主程序**：任意 `.exe`，支持附加文件/文件夹随包安装
- 📌 **桌面快捷方式**：安装时自动创建（可选，另支持开始菜单快捷方式）
- ⚡ **开机自启**：写入 `HKCU\...\Run` 注册表（可选）
- 🗑️ **卸载程序**：自动部署 `uninstall.exe`，并注册到系统"已安装的应用"面板，一键清理全部痕迹
- 🎨 **Google Material 风格 UI**：生成器、安装器、卸载器三套界面统一风格
- 📦 **单文件产物**：生成独立的 `setup.exe`，可分发给任意 Windows 用户
- 🔧 **无管理员依赖**：当前用户级安装（`%LOCALAPPDATA%\Programs\<应用名>`），免 UAC
- 🤫 **静默安装/卸载**：支持 `--silent` 参数，适合自动化部署

## 快速开始

### 方式一：使用成品

从 [Releases](../../releases) 下载 **`InstallerBuilder.exe`**（Windows 可直接运行，无需 Python 环境）。

### 方式二：从源码运行

```bash
# 需要 Python 3.9+ 与 PyInstaller
pip install pyinstaller pillow
cd builder
python pack_builder.py        # 或双击 run.bat
```

## 使用步骤

1. 填写**应用信息**（名称、版本、公司/作者）
2. **选择主程序**（`.exe`）；依赖文件/文件夹通过"添加"加入附加列表
3. 勾选安装选项：桌面快捷方式 / 开始菜单快捷方式 / 开机自启
4. 可选：自定义图标（`.ico/.png/.jpg`，留空用默认图标）；选择输出目录
5. 点击 **生成安装包**，约 1~3 分钟后得到：

| 产物 | 说明 |
|---|---|
| `setup_<应用名>.exe` | 安装程序，双击即可安装 |
| `uninstall.exe` | 卸载程序（安装时自动部署，无需手动分发） |
| `安装信息.json` | 本次构建的元信息 |

### 安装行为

- 默认安装到 `%LOCALAPPDATA%\Programs\<应用名>`，安装时可修改路径
- 按勾选创建桌面/开始菜单快捷方式（指向主程序，使用应用图标）
- 勾选"开机自启"时写入 `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`
- 注册到 `HKCU\...\Uninstall\<应用名>`，可在 Windows **设置 → 应用 → 已安装的应用** 中查看并卸载
- 静默安装：`setup_<应用名>.exe --silent`

### 卸载行为

- 通过系统设置卸载，或运行安装目录下的 `uninstall.exe`
- 删除：桌面/开始菜单快捷方式、开机自启注册项、卸载注册项、整个安装目录
- 静默卸载：`uninstall.exe --silent`

## 从源码构建生成器为独立 exe（可选）

```bash
cd builder
python build_gui.py           # 或双击 build_gui.bat
# 产物：builder/dist/安装包制作器.exe
```

## 目录结构

```
├── builder/
│   ├── pack_builder.py              # 生成器主程序（Google 风格 GUI）
│   ├── builder_core.py              # 打包核心：模板渲染 / 图标 / PyInstaller 构建
│   ├── templates/
│   │   ├── installer_template.py    # 安装器源码模板（打成 setup.exe）
│   │   └── uninstaller_template.py  # 卸载器源码模板（打成 uninstall.exe）
│   ├── assets/                      # 默认图标资源
│   ├── run.bat                      # 双击运行生成器
│   └── build_gui.py                 # 将生成器打包为独立 exe
└── 使用说明.md
```

## 工作原理

1. **生成器** 渲染安装器/卸载器源码模板（注入应用名、版本、选项等配置）
2. 调用 **PyInstaller** 将卸载器、安装器分别打包为独立 exe
3. `setup.exe` 内嵌主程序负载；安装时解压到目标目录 → 部署 `uninstall.exe` → 创建快捷方式 → 写自启/卸载注册表
4. `uninstall.exe` 清理快捷方式、自启项、卸载注册项，并延迟删除安装目录

## 技术栈

- Python 3（tkinter 标准库 GUI）
- PyInstaller（打包分发）
- 无第三方运行时依赖（图标生成可选 Pillow）

## 许可证

[MIT](LICENSE) © 2026 tanle-mtr
