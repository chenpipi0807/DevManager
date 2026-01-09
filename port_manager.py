"""端口管理核心模块 - 智能端口分配、冲突检测、占用扫描"""
import socket
import psutil
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json
import os

PORT_CONFIG_FILE = os.path.join(os.path.dirname(__file__), "port_config.json")


@dataclass
class PortAllocation:
    """端口分配记录"""
    port: int
    project_id: str
    project_name: str
    service_key: str
    service_name: str
    tech_stack: str
    allocated_at: str
    last_used: str
    
    def to_dict(self) -> dict:
        return {
            "port": self.port,
            "project_id": self.project_id,
            "project_name": self.project_name,
            "service_key": self.service_key,
            "service_name": self.service_name,
            "tech_stack": self.tech_stack,
            "allocated_at": self.allocated_at,
            "last_used": self.last_used
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "PortAllocation":
        return cls(**data)


@dataclass
class PortRange:
    """端口范围配置"""
    name: str
    start: int
    end: int
    tech_stacks: List[str]
    description: str = ""


class PortManager:
    """端口管理器 - 智能分配、冲突检测、占用扫描"""
    
    # 预定义端口范围（按技术栈分类）
    PORT_RANGES = {
        "frontend_dev": PortRange(
            name="前端开发服务器",
            start=3000,
            end=3999,
            tech_stacks=["react", "vue", "vite", "webpack", "create-react-app"],
            description="React/Vue开发服务器默认范围"
        ),
        "frontend_vite": PortRange(
            name="Vite专用",
            start=5170,
            end=5199,
            tech_stacks=["vite"],
            description="Vite默认5173及邻近端口"
        ),
        "backend_python": PortRange(
            name="Python后端",
            start=8000,
            end=8099,
            tech_stacks=["fastapi", "flask", "django", "uvicorn"],
            description="Python Web框架常用范围"
        ),
        "backend_node": PortRange(
            name="Node.js后端",
            start=4000,
            end=4099,
            tech_stacks=["express", "koa", "nestjs"],
            description="Node.js后端服务"
        ),
        "custom": PortRange(
            name="自定义服务",
            start=9000,
            end=9999,
            tech_stacks=["custom"],
            description="其他自定义服务"
        )
    }
    
    # 技术栈默认端口
    DEFAULT_PORTS = {
        "vite": 5173,
        "react": 3000,
        "vue": 8080,
        "create-react-app": 3000,
        "webpack-dev-server": 8080,
        "fastapi": 8000,
        "flask": 5000,
        "django": 8000,
        "uvicorn": 8000,
        "express": 3000,
        "nestjs": 3000,
    }
    
    def __init__(self):
        self.allocations: Dict[int, PortAllocation] = {}
        self.load()
    
    def load(self):
        """加载端口分配记录"""
        if os.path.exists(PORT_CONFIG_FILE):
            try:
                with open(PORT_CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for alloc in data.get("allocations", []):
                        allocation = PortAllocation.from_dict(alloc)
                        self.allocations[allocation.port] = allocation
            except Exception as e:
                print(f"加载端口配置失败: {e}")
    
    def save(self):
        """保存端口分配记录"""
        data = {
            "allocations": [a.to_dict() for a in self.allocations.values()],
            "updated_at": datetime.now().isoformat()
        }
        with open(PORT_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def is_port_available(self, port: int) -> bool:
        """检查端口是否可用（未被占用）"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                s.bind(("127.0.0.1", port))
                return True
        except (socket.error, OSError):
            return False
    
    def get_port_occupant(self, port: int) -> Optional[Dict]:
        """获取占用端口的进程信息"""
        try:
            for conn in psutil.net_connections(kind='inet'):
                if conn.laddr.port == port and conn.status == 'LISTEN':
                    try:
                        proc = psutil.Process(conn.pid)
                        return {
                            "pid": conn.pid,
                            "name": proc.name(),
                            "cmdline": " ".join(proc.cmdline()),
                            "status": proc.status()
                        }
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        return {"pid": conn.pid, "name": "Unknown", "cmdline": "", "status": ""}
        except (psutil.AccessDenied, PermissionError):
            pass
        return None
    
    def scan_occupied_ports(self, port_range: Optional[Tuple[int, int]] = None) -> Dict[int, Dict]:
        """扫描指定范围内被占用的端口"""
        occupied = {}
        start, end = port_range or (1024, 65535)
        
        try:
            for conn in psutil.net_connections(kind='inet'):
                if conn.laddr.port >= start and conn.laddr.port <= end and conn.status == 'LISTEN':
                    port = conn.laddr.port
                    if port not in occupied:
                        occupant = self.get_port_occupant(port)
                        if occupant:
                            occupied[port] = occupant
        except (psutil.AccessDenied, PermissionError):
            pass
        
        return occupied
    
    def detect_tech_stack(self, command: str, cwd: str) -> str:
        """根据命令和工作目录检测技术栈"""
        command_lower = command.lower()
        
        # 前端技术栈检测
        if "npm run dev" in command_lower or "vite" in command_lower:
            return "vite"
        if "npm start" in command_lower or "react-scripts" in command_lower:
            return "create-react-app"
        if "vue-cli-service" in command_lower:
            return "vue"
        if "webpack-dev-server" in command_lower:
            return "webpack-dev-server"
        
        # Python后端检测
        if "uvicorn" in command_lower or "fastapi" in command_lower:
            return "fastapi"
        if "flask run" in command_lower or "flask" in command_lower:
            return "flask"
        if "django" in command_lower or "manage.py runserver" in command_lower:
            return "django"
        if "python" in command_lower and any(x in command_lower for x in ["main.py", "app.py", "run.py"]):
            # 检查目录中是否有框架特征文件
            if os.path.exists(os.path.join(cwd, "requirements.txt")):
                try:
                    with open(os.path.join(cwd, "requirements.txt"), "r") as f:
                        content = f.read().lower()
                        if "fastapi" in content:
                            return "fastapi"
                        if "flask" in content:
                            return "flask"
                except:
                    pass
            return "python"
        
        # Node.js后端检测
        if "express" in command_lower:
            return "express"
        if "nest" in command_lower:
            return "nestjs"
        
        return "custom"
    
    def suggest_port(self, tech_stack: str, project_id: str, exclude_ports: Set[int] = None) -> int:
        """根据技术栈智能建议端口"""
        exclude_ports = exclude_ports or set()
        
        # 1. 尝试使用默认端口
        default_port = self.DEFAULT_PORTS.get(tech_stack)
        if default_port and default_port not in exclude_ports:
            if self.is_port_available(default_port):
                # 检查是否已分配给其他项目
                if default_port not in self.allocations or self.allocations[default_port].project_id == project_id:
                    return default_port
        
        # 2. 在对应技术栈范围内查找可用端口
        for range_key, port_range in self.PORT_RANGES.items():
            if tech_stack in port_range.tech_stacks:
                for port in range(port_range.start, port_range.end + 1):
                    if port in exclude_ports:
                        continue
                    if self.is_port_available(port):
                        if port not in self.allocations or self.allocations[port].project_id == project_id:
                            return port
        
        # 3. 在自定义范围查找
        custom_range = self.PORT_RANGES["custom"]
        for port in range(custom_range.start, custom_range.end + 1):
            if port in exclude_ports:
                continue
            if self.is_port_available(port):
                if port not in self.allocations or self.allocations[port].project_id == project_id:
                    return port
        
        # 4. 实在找不到，返回一个高位端口
        for port in range(10000, 65535):
            if port in exclude_ports:
                continue
            if self.is_port_available(port):
                return port
        
        raise RuntimeError("无法找到可用端口")
    
    def allocate_port(self, port: int, project_id: str, project_name: str, 
                     service_key: str, service_name: str, tech_stack: str) -> PortAllocation:
        """分配端口"""
        now = datetime.now().isoformat()
        allocation = PortAllocation(
            port=port,
            project_id=project_id,
            project_name=project_name,
            service_key=service_key,
            service_name=service_name,
            tech_stack=tech_stack,
            allocated_at=now,
            last_used=now
        )
        self.allocations[port] = allocation
        self.save()
        return allocation
    
    def release_port(self, port: int):
        """释放端口"""
        if port in self.allocations:
            del self.allocations[port]
            self.save()
    
    def update_last_used(self, port: int):
        """更新端口最后使用时间"""
        if port in self.allocations:
            self.allocations[port].last_used = datetime.now().isoformat()
            self.save()
    
    def check_conflicts(self, projects: List) -> List[Dict]:
        """检查所有项目的端口冲突（跳过已修改端口的服务）"""
        conflicts = []
        port_usage = {}
        
        for project in projects:
            for service_key, service in project.services.items():
                if not service.enabled:
                    continue
                
                # 兼容新旧ServiceConfig
                port = getattr(service, 'port', None) or (service.port_config.port if hasattr(service, 'port_config') and service.port_config else None)
                if not port:
                    continue
                
                # 检查端口是否已被修改（如果已修改，说明用户已解决冲突，跳过）
                original_port = None
                if hasattr(service, 'port_config') and service.port_config:
                    original_port = service.port_config.original_port
                
                # 如果端口已被修改，不计入冲突检测
                if original_port and original_port != port:
                    continue
                
                if port not in port_usage:
                    port_usage[port] = []
                
                cwd = getattr(service, 'cwd', None) or getattr(service, 'working_dir', None)
                port_usage[port].append({
                    "project_id": project.id,
                    "project_name": project.name,
                    "service_key": service_key,
                    "service_name": service.name,
                    "command": service.command,
                    "cwd": cwd
                })
        
        # 找出冲突的端口
        for port, users in port_usage.items():
            if len(users) > 1:
                conflicts.append({
                    "port": port,
                    "users": users,
                    "severity": "high"
                })
        
        return conflicts
    
    def get_port_recommendations(self, project, service_key: str, service) -> Dict:
        """为服务获取端口建议"""
        cwd = getattr(service, 'cwd', None) or getattr(service, 'working_dir', None)
        tech_stack = self.detect_tech_stack(service.command, cwd)
        current_port = getattr(service, 'port', None) or (service.port_config.port if hasattr(service, 'port_config') and service.port_config else None)
        
        # 获取项目中已使用的端口
        used_ports = set()
        for s in project.services.values():
            port = getattr(s, 'port', None) or (s.port_config.port if hasattr(s, 'port_config') and s.port_config else None)
            if port:
                used_ports.add(port)
        
        recommendations = {
            "current_port": current_port,
            "tech_stack": tech_stack,
            "is_available": self.is_port_available(current_port) if current_port else None,
            "occupant": self.get_port_occupant(current_port) if current_port else None,
            "suggested_ports": []
        }
        
        # 生成3个建议端口
        exclude = used_ports.copy()
        if current_port:
            exclude.discard(current_port)
        
        for _ in range(3):
            try:
                suggested = self.suggest_port(tech_stack, project.id, exclude)
                recommendations["suggested_ports"].append(suggested)
                exclude.add(suggested)
            except:
                break
        
        return recommendations
    
    def get_all_allocations(self) -> List[PortAllocation]:
        """获取所有端口分配记录"""
        return sorted(self.allocations.values(), key=lambda x: x.port)
    
    def get_statistics(self) -> Dict:
        """获取端口使用统计"""
        stats = {
            "total_allocated": len(self.allocations),
            "by_tech_stack": {},
            "by_project": {},
            "port_ranges": {}
        }
        
        for alloc in self.allocations.values():
            # 按技术栈统计
            if alloc.tech_stack not in stats["by_tech_stack"]:
                stats["by_tech_stack"][alloc.tech_stack] = 0
            stats["by_tech_stack"][alloc.tech_stack] += 1
            
            # 按项目统计
            if alloc.project_name not in stats["by_project"]:
                stats["by_project"][alloc.project_name] = 0
            stats["by_project"][alloc.project_name] += 1
        
        # 按范围统计
        for range_key, port_range in self.PORT_RANGES.items():
            count = sum(1 for alloc in self.allocations.values() 
                       if port_range.start <= alloc.port <= port_range.end)
            stats["port_ranges"][range_key] = {
                "name": port_range.name,
                "range": f"{port_range.start}-{port_range.end}",
                "allocated": count,
                "total": port_range.end - port_range.start + 1
            }
        
        return stats


# 全局单例
port_manager = PortManager()
