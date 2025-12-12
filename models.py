"""数据模型定义"""
from dataclasses import dataclass, field
from typing import Dict, Optional
from datetime import datetime
import uuid
import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "projects.json")


@dataclass
class ServiceConfig:
    """服务配置"""
    enabled: bool = True
    name: str = ""
    command: str = ""
    cwd: str = ""
    port: Optional[int] = None
    env: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "name": self.name,
            "command": self.command,
            "cwd": self.cwd,
            "port": self.port,
            "env": self.env
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ServiceConfig":
        return cls(
            enabled=data.get("enabled", True),
            name=data.get("name", ""),
            command=data.get("command", ""),
            cwd=data.get("cwd", ""),
            port=data.get("port"),
            env=data.get("env", {})
        )


@dataclass
class Project:
    """项目配置"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    path: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    services: Dict[str, ServiceConfig] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "path": self.path,
            "created_at": self.created_at,
            "services": {k: v.to_dict() for k, v in self.services.items()}
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Project":
        services = {}
        for k, v in data.get("services", {}).items():
            services[k] = ServiceConfig.from_dict(v)
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            description=data.get("description", ""),
            path=data.get("path", ""),
            created_at=data.get("created_at", datetime.now().isoformat()),
            services=services
        )


class ProjectManager:
    """项目管理器 - 负责项目的增删改查和持久化"""

    def __init__(self):
        self.projects: Dict[str, Project] = {}
        self.load()

    def load(self):
        """从文件加载项目配置"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for p in data.get("projects", []):
                        project = Project.from_dict(p)
                        self.projects[project.id] = project
            except Exception as e:
                print(f"加载配置失败: {e}")

    def save(self):
        """保存项目配置到文件"""
        data = {
            "projects": [p.to_dict() for p in self.projects.values()]
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add(self, project: Project) -> Project:
        """添加项目"""
        self.projects[project.id] = project
        self.save()
        return project

    def update(self, project: Project) -> Project:
        """更新项目"""
        self.projects[project.id] = project
        self.save()
        return project

    def delete(self, project_id: str):
        """删除项目"""
        if project_id in self.projects:
            del self.projects[project_id]
            self.save()

    def get(self, project_id: str) -> Optional[Project]:
        """获取项目"""
        return self.projects.get(project_id)

    def get_all(self) -> list:
        """获取所有项目"""
        return list(self.projects.values())
