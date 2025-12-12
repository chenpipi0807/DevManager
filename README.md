# DevManager - 本地开发项目管理面板

一个极简的本地 GUI 工具，用于管理多个开发项目的前后端服务（启动/停止/日志/进程扫描）。

<img width="1320" height="1086" alt="image" src="https://github.com/user-attachments/assets/1a8a312a-a64c-4e77-9d57-9742f38e1a0d" />


## 功能

- **项目管理**：添加/编辑/删除项目
- **服务管理**：每个项目可配置前端/后端服务，独立启停
- **智能识别**：选择项目路径后自动识别前后端（可手动修改）
- **日志查看**：实时查看输出（自动限制行数，避免内存爆炸）
- **进程扫描**：扫描系统中运行的开发进程，并按项目路径尝试匹配

## 快速开始

### 1) 安装依赖

```powershell
cd C:\DevManager
pip install -r requirements.txt
```

### 2) 启动

- **推荐**：双击 `start.bat`
- 或在 PowerShell（已激活 conda/base）运行：

```powershell
cd C:\DevManager
python main.py
```

## 配置文件

项目配置保存在 `projects.json`（程序运行后自动生成/更新）。

## 常见问题

### 运行时报 `No module named 'customtkinter'`

说明你当前使用的 `python` 环境没有安装依赖。

- 直接双击 `start.bat`
- 或使用 Anaconda 的 Python 运行：

```powershell
C:\ProgramData\anaconda3\python.exe C:\DevManager\main.py
```

### 任务栏图标不显示

已在程序内设置 Windows 的 AppUserModelID + `icon.ico`。
如果仍未生效，尝试关闭所有 DevManager 进程后重新启动。
