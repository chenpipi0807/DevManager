# DevManager

本地开发项目管理工具，统一管理多个前后端项目的启动、停止和端口配置。

## 核心功能

### 项目管理

- 自动检测前后端技术栈（FastAPI/Flask/Django + React/Vue/Vite）
- 一键启动/停止项目所有服务
- 实时查看服务日志

### 端口管理

- 智能端口分配和冲突检测
- 查看系统端口占用情况
- 支持端口映射配置

### Python环境

- 自动检测系统Python环境
- 为每个后端服务指定Python版本

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 启动应用

```bash
# Windows
start.bat

# 或直接运行
python main.py
```

### 使用流程

1. 点击「添加项目」选择项目目录
2. 系统自动检测技术栈和端口配置
3. 点击「启动」运行服务
4. 通过「端口管理」查看端口使用情况

## 配置文件

- `projects_v2.json` - 项目配置
- `port_config.json` - 端口分配记录
