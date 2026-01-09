"""项目检测器 - 智能识别项目结构和启动命令"""
import os
import json
from dataclasses import dataclass
from typing import List, Optional, Tuple
from port_manager import port_manager
from port_detector import port_detector, PortDetectionResult


@dataclass
class DetectedService:
    """检测到的服务"""
    name: str
    command: str
    cwd: str
    port: Optional[int] = None
    confidence: float = 0.0  # 置信度 0-1
    tech_stack: str = "custom"  # 技术栈标识
    port_source: str = ""  # 端口来源
    port_confidence: float = 0.0  # 端口检测置信度
    env_var: Optional[str] = None  # 环境变量名


@dataclass
class DetectedProject:
    """检测到的项目信息"""
    name: str
    path: str
    description: str = ""
    backend: Optional[DetectedService] = None
    frontend: Optional[DetectedService] = None


class ProjectDetector:
    """项目检测器"""

    DEFAULT_PYTHON_EXE = r"C:\ProgramData\anaconda3\python.exe"

    # 后端框架特征
    BACKEND_PATTERNS = {
        # Python
        "fastapi": {
            "files": ["main.py", "app.py", "server.py"],
            "markers": ["fastapi", "uvicorn"],
            "command": "{python} {file}",
            "alt_command": "{python} -m uvicorn {module}:app --reload",
            "default_port": 8000
        },
        "flask": {
            "files": ["app.py", "main.py", "run.py"],
            "markers": ["flask", "Flask"],
            "command": "{python} {file}",
            "alt_command": "flask run",
            "default_port": 5000
        },
        "django": {
            "files": ["manage.py"],
            "markers": ["django"],
            "command": "{python} manage.py runserver",
            "default_port": 8000
        },
        "express": {
            "files": ["server.js", "app.js", "index.js"],
            "markers": ["express"],
            "command": "node {file}",
            "default_port": 3000
        },
        "go": {
            "files": ["main.go"],
            "markers": [],
            "command": "go run main.go",
            "default_port": 8080
        },
    }

    # 前端框架特征
    FRONTEND_PATTERNS = {
        "vite": {
            "markers": ["vite", "@vitejs"],
            "command": "npm run dev",
            "default_port": 5173
        },
        "create-react-app": {
            "markers": ["react-scripts"],
            "command": "npm start",
            "default_port": 3000
        },
        "next": {
            "markers": ["next"],
            "command": "npm run dev",
            "default_port": 3000
        },
        "vue-cli": {
            "markers": ["@vue/cli-service"],
            "command": "npm run serve",
            "default_port": 8080
        },
        "nuxt": {
            "markers": ["nuxt"],
            "command": "npm run dev",
            "default_port": 3000
        },
        "angular": {
            "markers": ["@angular/cli"],
            "command": "ng serve",
            "default_port": 4200
        },
    }

    def detect(self, project_path: str) -> DetectedProject:
        """检测项目结构"""
        project_path = os.path.abspath(project_path)
        project_name = os.path.basename(project_path)

        result = DetectedProject(
            name=project_name,
            path=project_path
        )

        # 扫描目录结构
        self._scan_directory(project_path, result)

        return result

    def _scan_directory(self, path: str, result: DetectedProject, depth: int = 0):
        """递归扫描目录"""
        if depth > 3:  # 最多扫描3层
            return

        try:
            items = os.listdir(path)
        except PermissionError:
            return

        # 检查当前目录
        self._check_backend(path, items, result)
        self._check_frontend(path, items, result)

        # 递归检查子目录（优先检查常见目录名）
        priority_dirs = ["backend", "server", "api", "frontend", "client", "web", "web_app", "src"]
        
        for dir_name in priority_dirs:
            if dir_name in items:
                sub_path = os.path.join(path, dir_name)
                if os.path.isdir(sub_path):
                    self._scan_directory(sub_path, result, depth + 1)

        # 检查其他目录
        for item in items:
            if item.startswith('.') or item in priority_dirs:
                continue
            if item in ['node_modules', '__pycache__', 'venv', '.venv', 'dist', 'build']:
                continue
            
            sub_path = os.path.join(path, item)
            if os.path.isdir(sub_path):
                self._scan_directory(sub_path, result, depth + 1)

    def _check_backend(self, path: str, items: List[str], result: DetectedProject):
        """检查后端项目"""
        if result.backend and result.backend.confidence > 0.8:
            return  # 已经找到高置信度的后端

        python_exe = os.environ.get("DEV_MANAGER_PYTHON_EXE", self.DEFAULT_PYTHON_EXE)

        # 检查 Python 后端
        for py_file in ["main.py", "app.py", "server.py", "run.py"]:
            if py_file in items:
                file_path = os.path.join(path, py_file)
                framework, confidence = self._detect_python_framework(file_path)
                
                if confidence > (result.backend.confidence if result.backend else 0):
                    pattern = self.BACKEND_PATTERNS.get(framework, {})
                    command_template = pattern.get("command", "{python} {file}")
                    command = command_template.format(python=python_exe, file=py_file)
                    
                    # 使用深度端口检测器
                    port_result = port_detector.detect_backend_port(path)
                    
                    # 检查命令中的端口覆盖
                    env_override = port_detector.detect_env_port_override(command)
                    
                    final_port = None
                    port_source = "默认"
                    port_conf = 0.0
                    env_var = None
                    
                    if env_override:
                        env_var, final_port = env_override
                        port_source = f"命令行 ({env_var}={final_port})"
                        port_conf = 1.0
                    elif port_result.port:
                        final_port = port_result.port
                        port_source = port_result.source
                        port_conf = port_result.confidence
                        env_var = port_result.env_var
                    else:
                        final_port = port_manager.suggest_port(framework, "", set())
                        port_source = "智能建议"
                        port_conf = 0.5
                    
                    result.backend = DetectedService(
                        name="后端服务",
                        command=command,
                        cwd=path,
                        port=final_port,
                        confidence=confidence,
                        tech_stack=framework,
                        port_source=port_source,
                        port_confidence=port_conf,
                        env_var=env_var
                    )

        # 检查 Django
        if "manage.py" in items:
            suggested_port = port_manager.suggest_port("django", "", set())
            result.backend = DetectedService(
                name="后端服务 (Django)",
                command=f"{python_exe} manage.py runserver",
                cwd=path,
                port=suggested_port,
                confidence=0.9,
                tech_stack="django"
            )

        # 检查 Node.js 后端
        if "package.json" in items and not result.backend:
            pkg_path = os.path.join(path, "package.json")
            if self._is_node_backend(pkg_path):
                for js_file in ["server.js", "app.js", "index.js"]:
                    if js_file in items:
                        suggested_port = port_manager.suggest_port("express", "", set())
                        result.backend = DetectedService(
                            name="后端服务 (Node.js)",
                            command=f"node {js_file}",
                            cwd=path,
                            port=suggested_port,
                            confidence=0.7,
                            tech_stack="express"
                        )
                        break

        # 检查 Go 后端
        if "main.go" in items and not result.backend:
            result.backend = DetectedService(
                name="后端服务 (Go)",
                command="go run main.go",
                cwd=path,
                port=8080,
                confidence=0.8,
                tech_stack="go"
            )

    def _check_frontend(self, path: str, items: List[str], result: DetectedProject):
        """检查前端项目"""
        if result.frontend and result.frontend.confidence > 0.8:
            return

        if "package.json" not in items:
            return

        pkg_path = os.path.join(path, "package.json")
        framework, command, port, confidence = self._detect_frontend_framework(pkg_path)

        if confidence > (result.frontend.confidence if result.frontend else 0):
            tech_stack = framework or "react"
            
            # 使用深度端口检测器
            port_result = port_detector.detect_frontend_port(path)
            
            # 检查命令中的端口覆盖
            env_override = port_detector.detect_env_port_override(command)
            
            final_port = None
            port_source = "默认"
            port_conf = 0.0
            env_var = None
            
            if env_override:
                # 命令中有明确的端口覆盖
                env_var, final_port = env_override
                port_source = f"命令行 ({env_var}={final_port})"
                port_conf = 1.0
            elif port_result.port:
                # 从配置文件读取到端口
                final_port = port_result.port
                port_source = port_result.source
                port_conf = port_result.confidence
                env_var = port_result.env_var
            else:
                # 使用智能建议
                used_ports = {result.backend.port} if result.backend and result.backend.port else set()
                final_port = port_manager.suggest_port(tech_stack, "", used_ports)
                port_source = "智能建议"
                port_conf = 0.5
            
            result.frontend = DetectedService(
                name=f"前端服务 ({framework})" if framework else "前端服务",
                command=command,
                cwd=path,
                port=final_port,
                confidence=confidence,
                tech_stack=tech_stack,
                port_source=port_source,
                port_confidence=port_conf,
                env_var=env_var
            )

    def _detect_python_framework(self, file_path: str) -> tuple:
        """检测 Python 框架"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(5000)  # 只读前5000字符
                
            if 'fastapi' in content.lower() or 'FastAPI' in content:
                return 'fastapi', 0.9
            if 'flask' in content.lower() or 'Flask' in content:
                return 'flask', 0.9
            if 'django' in content.lower():
                return 'django', 0.8
            
            # 通用 Python 服务
            if 'uvicorn' in content or 'gunicorn' in content:
                return 'fastapi', 0.7
            
            return 'python', 0.5
        except:
            return 'python', 0.3

    def _detect_frontend_framework(self, pkg_path: str) -> tuple:
        """检测前端框架，返回 (framework, command, port, confidence)"""
        try:
            with open(pkg_path, 'r', encoding='utf-8') as f:
                pkg = json.load(f)
        except:
            return None, "npm run dev", 3000, 0.3

        deps = {}
        deps.update(pkg.get('dependencies', {}))
        deps.update(pkg.get('devDependencies', {}))

        scripts = pkg.get('scripts', {})

        # 检测框架
        for framework, pattern in self.FRONTEND_PATTERNS.items():
            for marker in pattern['markers']:
                if marker in deps:
                    command = pattern['command']
                    # 检查 scripts 中是否有对应命令
                    if 'dev' in scripts:
                        command = 'npm run dev'
                    elif 'start' in scripts:
                        command = 'npm start'
                    elif 'serve' in scripts:
                        command = 'npm run serve'
                    
                    return framework, command, pattern['default_port'], 0.9

        # 通用前端项目
        if 'dev' in scripts:
            return None, 'npm run dev', 3000, 0.6
        if 'start' in scripts:
            return None, 'npm start', 3000, 0.6

        return None, 'npm run dev', 3000, 0.3

    def _is_node_backend(self, pkg_path: str) -> bool:
        """判断是否是 Node.js 后端项目"""
        try:
            with open(pkg_path, 'r', encoding='utf-8') as f:
                pkg = json.load(f)
            
            deps = {}
            deps.update(pkg.get('dependencies', {}))
            
            # 后端特征
            backend_markers = ['express', 'koa', 'fastify', 'hapi', 'nest']
            # 前端特征
            frontend_markers = ['react', 'vue', 'angular', '@angular', 'svelte', 'vite']
            
            has_backend = any(m in deps for m in backend_markers)
            has_frontend = any(m in deps for m in frontend_markers)
            
            return has_backend and not has_frontend
        except:
            return False


# 全局实例
project_detector = ProjectDetector()


def detect_project(path: str) -> DetectedProject:
    """检测项目"""
    return project_detector.detect(path)
