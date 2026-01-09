"""增强的企业级项目配置模型"""
from dataclasses import dataclass, field
from typing import Dict, Optional, List
from datetime import datetime
import uuid
import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "projects_v2.json")


@dataclass
class PythonEnvironment:
    """Python环境配置"""
    path: str  # Python可执行文件路径
    name: str = ""  # 环境名称（如 base, myenv）
    version: str = ""  # Python版本
    is_conda: bool = False  # 是否是Conda环境
    
    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "name": self.name,
            "version": self.version,
            "is_conda": self.is_conda
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "PythonEnvironment":
        return cls(
            path=data.get("path", ""),
            name=data.get("name", ""),
            version=data.get("version", ""),
            is_conda=data.get("is_conda", False)
        )


@dataclass
class PortConfig:
    """端口配置"""
    port: int  # 当前使用的端口
    original_port: Optional[int] = None  # 原始检测到的端口（用于对比）
    detected_port: Optional[int] = None  # 检测到的端口（兼容旧版）
    port_source: str = ""  # 端口来源（如 vite.config.js, .env）
    port_source_file: str = ""  # 端口来源文件路径
    mapped_port: Optional[int] = None  # 映射端口（已废弃）
    confidence: float = 0.0  # 检测置信度
    
    def to_dict(self) -> dict:
        return {
            "port": self.port,
            "original_port": self.original_port,
            "detected_port": self.detected_port,
            "port_source": self.port_source,
            "port_source_file": self.port_source_file,
            "mapped_port": self.mapped_port,
            "confidence": self.confidence
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "PortConfig":
        return cls(
            port=data.get("port", 3000),
            original_port=data.get("original_port"),
            detected_port=data.get("detected_port"),
            port_source=data.get("port_source", ""),
            port_source_file=data.get("port_source_file", ""),
            mapped_port=data.get("mapped_port"),
            confidence=data.get("confidence", 0.0)
        )


@dataclass
class ServiceConfig:
    """服务配置（前端/后端/其他服务）"""
    enabled: bool = True
    name: str = ""
    service_type: str = ""  # frontend, backend, service
    tech_stack: str = ""  # vite, react, fastapi, django等
    
    # 路径配置
    working_dir: str = ""  # 工作目录
    startup_file: str = ""  # 启动文件（如 main.py, package.json）
    
    # 启动命令
    command: str = ""
    command_template: str = ""  # 命令模板（支持变量替换）
    
    # 端口配置
    port_config: Optional[PortConfig] = None
    
    # Python环境（仅后端）
    python_env: Optional[PythonEnvironment] = None
    
    # 环境变量
    env_vars: Dict[str, str] = field(default_factory=dict)
    
    # 依赖服务
    depends_on: List[str] = field(default_factory=list)  # 依赖的其他服务key
    
    # 日志配置
    log_file: str = ""  # 日志文件路径
    log_level: str = "INFO"  # 日志级别
    
    # 元数据
    auto_detected: bool = False  # 是否自动检测
    last_modified: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "name": self.name,
            "service_type": self.service_type,
            "tech_stack": self.tech_stack,
            "working_dir": self.working_dir,
            "startup_file": self.startup_file,
            "command": self.command,
            "command_template": self.command_template,
            "port_config": self.port_config.to_dict() if self.port_config else None,
            "python_env": self.python_env.to_dict() if self.python_env else None,
            "env_vars": self.env_vars,
            "depends_on": self.depends_on,
            "log_file": self.log_file,
            "log_level": self.log_level,
            "auto_detected": self.auto_detected,
            "last_modified": self.last_modified
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ServiceConfig":
        port_config = None
        if data.get("port_config"):
            port_config = PortConfig.from_dict(data["port_config"])
        
        python_env = None
        if data.get("python_env"):
            python_env = PythonEnvironment.from_dict(data["python_env"])
        
        return cls(
            enabled=data.get("enabled", True),
            name=data.get("name", ""),
            service_type=data.get("service_type", ""),
            tech_stack=data.get("tech_stack", ""),
            working_dir=data.get("working_dir", ""),
            startup_file=data.get("startup_file", ""),
            command=data.get("command", ""),
            command_template=data.get("command_template", ""),
            port_config=port_config,
            python_env=python_env,
            env_vars=data.get("env_vars", {}),
            depends_on=data.get("depends_on", []),
            log_file=data.get("log_file", ""),
            log_level=data.get("log_level", "INFO"),
            auto_detected=data.get("auto_detected", False),
            last_modified=data.get("last_modified", datetime.now().isoformat())
        )


@dataclass
class ProjectMetadata:
    """项目元数据"""
    tags: List[str] = field(default_factory=list)  # 标签
    category: str = ""  # 分类
    priority: str = "normal"  # 优先级: low, normal, high
    status: str = "active"  # 状态: active, archived, maintenance
    notes: str = ""  # 备注
    
    def to_dict(self) -> dict:
        return {
            "tags": self.tags,
            "category": self.category,
            "priority": self.priority,
            "status": self.status,
            "notes": self.notes
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ProjectMetadata":
        return cls(
            tags=data.get("tags", []),
            category=data.get("category", ""),
            priority=data.get("priority", "normal"),
            status=data.get("status", "active"),
            notes=data.get("notes", "")
        )


@dataclass
class Project:
    """增强的项目配置"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    path: str = ""  # 项目根路径
    
    # 服务配置
    services: Dict[str, ServiceConfig] = field(default_factory=dict)
    
    # 项目元数据
    metadata: ProjectMetadata = field(default_factory=ProjectMetadata)
    
    # 时间戳
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_run_at: Optional[str] = None
    
    # 项目配置
    config_version: str = "2.0"  # 配置版本
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "path": self.path,
            "services": {k: v.to_dict() for k, v in self.services.items()},
            "metadata": self.metadata.to_dict(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_run_at": self.last_run_at,
            "config_version": self.config_version
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Project":
        services = {}
        for k, v in data.get("services", {}).items():
            services[k] = ServiceConfig.from_dict(v)
        
        metadata = ProjectMetadata.from_dict(data.get("metadata", {}))
        
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            description=data.get("description", ""),
            path=data.get("path", ""),
            services=services,
            metadata=metadata,
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            last_run_at=data.get("last_run_at"),
            config_version=data.get("config_version", "2.0")
        )


class EnhancedProjectManager:
    """增强的项目管理器"""
    
    def __init__(self):
        self.projects: Dict[str, Project] = {}
        self.config_file = CONFIG_FILE
        self.load()
    
    def load(self):
        """从文件加载项目配置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for p in data.get("projects", []):
                        project = Project.from_dict(p)
                        self.projects[project.id] = project
            except Exception as e:
                print(f"加载配置失败: {e}")
    
    def save(self):
        """保存项目配置到文件"""
        data = {
            "version": "2.0",
            "last_updated": datetime.now().isoformat(),
            "projects": [p.to_dict() for p in self.projects.values()]
        }
        
        # 备份旧配置
        if os.path.exists(self.config_file):
            backup_file = self.config_file + ".backup"
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    backup_data = f.read()
                with open(backup_file, "w", encoding="utf-8") as f:
                    f.write(backup_data)
            except:
                pass
        
        # 保存新配置
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add(self, project: Project) -> Project:
        """添加项目"""
        project.updated_at = datetime.now().isoformat()
        self.projects[project.id] = project
        self.save()
        return project
    
    def update(self, project: Project) -> Project:
        """更新项目"""
        project.updated_at = datetime.now().isoformat()
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
    
    def get_all(self) -> List[Project]:
        """获取所有项目"""
        return list(self.projects.values())
    
    def get_by_status(self, status: str) -> List[Project]:
        """按状态获取项目"""
        return [p for p in self.projects.values() if p.metadata.status == status]
    
    def search(self, keyword: str) -> List[Project]:
        """搜索项目"""
        keyword = keyword.lower()
        results = []
        for project in self.projects.values():
            if (keyword in project.name.lower() or 
                keyword in project.description.lower() or
                keyword in project.path.lower()):
                results.append(project)
        return results
    
    def update_last_run(self, project_id: str):
        """更新最后运行时间"""
        if project_id in self.projects:
            self.projects[project_id].last_run_at = datetime.now().isoformat()
            self.save()
    
    def migrate_from_old_config(self, old_config_file: str):
        """从旧配置迁移"""
        if not os.path.exists(old_config_file):
            return
        
        try:
            with open(old_config_file, "r", encoding="utf-8") as f:
                old_data = json.load(f)
            
            for old_project in old_data.get("projects", []):
                # 创建新项目
                project = Project(
                    id=old_project.get("id", str(uuid.uuid4())),
                    name=old_project.get("name", ""),
                    description=old_project.get("description", ""),
                    path=old_project.get("path", ""),
                    created_at=old_project.get("created_at", datetime.now().isoformat())
                )
                
                # 迁移服务配置
                for service_key, old_service in old_project.get("services", {}).items():
                    service = ServiceConfig(
                        enabled=old_service.get("enabled", True),
                        name=old_service.get("name", ""),
                        working_dir=old_service.get("cwd", ""),
                        command=old_service.get("command", ""),
                        env_vars=old_service.get("env", {}),
                        auto_detected=True
                    )
                    
                    # 迁移端口配置
                    if old_service.get("port"):
                        service.port_config = PortConfig(
                            port=old_service["port"],
                            detected_port=old_service["port"]
                        )
                    
                    project.services[service_key] = service
                
                self.projects[project.id] = project
            
            self.save()
            print(f"成功迁移 {len(self.projects)} 个项目")
        except Exception as e:
            print(f"迁移失败: {e}")


# 全局实例
enhanced_project_manager = EnhancedProjectManager()
