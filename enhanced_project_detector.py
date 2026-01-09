"""增强的项目检测器 - 集成深度端口检测和Python环境检测"""
import os
import json
import subprocess
import glob
from dataclasses import dataclass
from typing import Optional, List, Dict
from port_detector import port_detector, PortDetectionResult
from enhanced_models import (
    ServiceConfig, PortConfig, PythonEnvironment,
    ProjectMetadata
)


@dataclass
class DetectedService:
    """检测到的服务信息"""
    service_type: str  # frontend, backend, service
    name: str
    tech_stack: str
    working_dir: str
    startup_file: str
    command: str
    command_template: str
    port_config: Optional[PortConfig] = None
    python_env: Optional[PythonEnvironment] = None
    env_vars: Dict[str, str] = None
    confidence: float = 0.0
    
    def __post_init__(self):
        if self.env_vars is None:
            self.env_vars = {}


class EnhancedProjectDetector:
    """增强的项目检测器"""
    
    def __init__(self):
        self.available_python_envs = []
        self._detect_python_environments()
    
    def _detect_python_environments(self):
        """检测所有可用的Python环境"""
        envs = []
        
        # 1. 使用where命令查找Python
        try:
            result = subprocess.run(
                ["where", "python"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    path = line.strip()
                    if path and os.path.exists(path):
                        env = self._get_python_info(path)
                        if env:
                            envs.append(env)
        except:
            pass
        
        # 2. 检测Conda环境
        try:
            result = subprocess.run(
                ["conda", "env", "list"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.strip() and not line.startswith('#'):
                        parts = line.split()
                        if len(parts) >= 2:
                            env_name = parts[0]
                            env_path = parts[-1]
                            python_path = os.path.join(env_path, "python.exe")
                            if os.path.exists(python_path):
                                env = self._get_python_info(python_path, env_name, True)
                                if env and not any(e.path == env.path for e in envs):
                                    envs.append(env)
        except:
            pass
        
        # 3. 扫描常见安装路径
        common_paths = [
            "C:/Python*",
            "C:/Program Files/Python*",
            "C:/ProgramData/anaconda3",
            "C:/ProgramData/miniconda3",
            os.path.expanduser("~/anaconda3"),
            os.path.expanduser("~/miniconda3"),
            os.path.expanduser("~/AppData/Local/Programs/Python/Python*")
        ]
        
        for pattern in common_paths:
            for path in glob.glob(pattern):
                python_path = os.path.join(path, "python.exe")
                if os.path.exists(python_path):
                    env = self._get_python_info(python_path)
                    if env and not any(e.path == env.path for e in envs):
                        envs.append(env)
        
        self.available_python_envs = envs
    
    def _get_python_info(self, python_path: str, name: str = "", is_conda: bool = False) -> Optional[PythonEnvironment]:
        """获取Python环境信息"""
        try:
            result = subprocess.run(
                [python_path, "--version"],
                capture_output=True,
                text=True,
                timeout=3
            )
            if result.returncode == 0:
                version = result.stdout.strip() or result.stderr.strip()
                
                if not name:
                    # 从路径推断名称
                    if "anaconda3" in python_path.lower():
                        name = "anaconda3"
                    elif "miniconda3" in python_path.lower():
                        name = "miniconda3"
                    else:
                        name = os.path.basename(os.path.dirname(python_path))
                
                if not is_conda:
                    is_conda = "anaconda" in python_path.lower() or "miniconda" in python_path.lower()
                
                return PythonEnvironment(
                    path=python_path,
                    name=name,
                    version=version,
                    is_conda=is_conda
                )
        except:
            pass
        return None
    
    def detect_project(self, project_path: str) -> Dict[str, DetectedService]:
        """检测项目结构"""
        services = {}
        
        # 如果指定路径下没有代码文件，尝试查找project/src等子目录
        actual_path = self._find_actual_project_path(project_path)
        
        # 检测前端
        frontend = self._detect_frontend(actual_path)
        if frontend:
            services['frontend'] = frontend
        
        # 检测后端
        backend = self._detect_backend(actual_path)
        if backend:
            services['backend'] = backend
        
        return services
    
    def _find_actual_project_path(self, project_path: str) -> str:
        """查找实际的项目路径（处理project/src等中间目录）"""
        # 检查当前路径是否有代码文件
        has_package_json = os.path.exists(os.path.join(project_path, "package.json"))
        has_python_files = any(
            os.path.exists(os.path.join(project_path, f)) 
            for f in ['main.py', 'app.py', 'run.py', 'server.py']
        )
        has_subdirs = any(
            os.path.exists(os.path.join(project_path, d))
            for d in ['frontend', 'backend', 'src', 'app']
        )
        
        # 如果当前路径有代码或有前后端子目录，直接使用
        if has_package_json or has_python_files or has_subdirs:
            return project_path
        
        # 否则，尝试查找project/src等常见的项目目录
        for subdir in ['project', 'src', 'code', 'source']:
            subdir_path = os.path.join(project_path, subdir)
            if os.path.exists(subdir_path):
                # 检查子目录是否有代码
                has_code = (
                    os.path.exists(os.path.join(subdir_path, "package.json")) or
                    any(os.path.exists(os.path.join(subdir_path, f)) for f in ['main.py', 'app.py']) or
                    os.path.exists(os.path.join(subdir_path, "frontend")) or
                    os.path.exists(os.path.join(subdir_path, "backend"))
                )
                if has_code:
                    return subdir_path
        
        # 如果都没找到，返回原路径
        return project_path
    
    def _detect_frontend(self, project_path: str) -> Optional[DetectedService]:
        """检测前端服务"""
        # 搜索package.json（支持多层级）
        package_json = None
        frontend_dir = project_path
        
        # 先检查根目录
        if os.path.exists(os.path.join(project_path, "package.json")):
            package_json = os.path.join(project_path, "package.json")
            frontend_dir = project_path
        else:
            # 搜索子目录（常见的前端目录名）
            for subdir in ['frontend', 'front', 'web', 'client', 'ui', 'app']:
                subdir_path = os.path.join(project_path, subdir)
                pkg_path = os.path.join(subdir_path, "package.json")
                if os.path.exists(pkg_path):
                    package_json = pkg_path
                    frontend_dir = subdir_path
                    break
        
        if not package_json:
            return None
        
        try:
            with open(package_json, 'r', encoding='utf-8') as f:
                pkg_data = json.load(f)
        except:
            return None
        
        # 判断技术栈
        tech_stack = "unknown"
        dependencies = pkg_data.get("dependencies", {})
        dev_dependencies = pkg_data.get("devDependencies", {})
        all_deps = {**dependencies, **dev_dependencies}
        
        if "vite" in all_deps:
            tech_stack = "vite"
        elif "react-scripts" in all_deps or "react" in dependencies:
            tech_stack = "react"
        elif "vue" in dependencies:
            tech_stack = "vue"
        elif "@angular/core" in dependencies:
            tech_stack = "angular"
        
        # 检测端口（使用正确的方法）
        port_result = port_detector.detect_frontend_port(frontend_dir)
        port_config = None
        if port_result and port_result.port:
            port_config = PortConfig(
                port=port_result.port,
                detected_port=port_result.port,
                port_source=port_result.source,
                port_source_file=port_result.details,
                confidence=port_result.confidence
            )
        else:
            # 默认端口
            default_port = 5173 if tech_stack == "vite" else 3000
            port_config = PortConfig(
                port=default_port,
                port_source="默认端口",
                confidence=0.3
            )
        
        # 生成启动命令
        scripts = pkg_data.get("scripts", {})
        command = "npm run dev"
        command_template = "npm run dev"
        
        if "dev" in scripts:
            command = "npm run dev"
        elif "start" in scripts:
            command = "npm start"
        
        # 如果是vite，添加端口参数
        if tech_stack == "vite":
            command_template = "npm run dev -- --port {port}"
        
        return DetectedService(
            service_type="frontend",
            name="前端服务",
            tech_stack=tech_stack,
            working_dir=frontend_dir,
            startup_file=package_json,
            command=command,
            command_template=command_template,
            port_config=port_config,
            confidence=0.9
        )
    
    def _detect_backend(self, project_path: str) -> Optional[DetectedService]:
        """检测后端服务"""
        # 搜索Python文件（支持多层级）
        backend_dir = project_path
        startup_file = None
        tech_stack = "python"
        
        # 常见的后端目录名和启动文件名
        backend_subdirs = ['backend', 'back', 'server', 'api', 'app', 'src']
        startup_filenames = ['main.py', 'app.py', 'run.py', 'server.py', 'manage.py', 'start.py', 'index.py']
        
        # 1. 先在根目录查找启动文件
        for filename in startup_filenames:
            filepath = os.path.join(project_path, filename)
            if os.path.exists(filepath):
                startup_file = filepath
                backend_dir = project_path
                break
        
        # 2. 如果根目录没找到，搜索子目录
        if not startup_file:
            for subdir in backend_subdirs:
                subdir_path = os.path.join(project_path, subdir)
                if os.path.exists(subdir_path):
                    for filename in startup_filenames:
                        filepath = os.path.join(subdir_path, filename)
                        if os.path.exists(filepath):
                            startup_file = filepath
                            backend_dir = subdir_path
                            break
                    if startup_file:
                        break
        
        # 3. 如果还是没找到，递归搜索所有Python文件
        if not startup_file:
            python_files = []
            for root, dirs, files in os.walk(project_path):
                # 跳过虚拟环境和node_modules
                dirs[:] = [d for d in dirs if d not in ['venv', 'env', '.venv', 'node_modules', '__pycache__', 'frontend', 'front', 'web', 'client']]
                for file in files:
                    if file.endswith('.py') and file in startup_filenames:
                        python_files.append(os.path.join(root, file))
            
            if python_files:
                startup_file = python_files[0]
                backend_dir = os.path.dirname(startup_file)
            else:
                return None
        
        # 检测技术栈（读取启动文件内容）
        if startup_file:
            try:
                with open(startup_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'fastapi' in content.lower() or 'FastAPI' in content:
                        tech_stack = "fastapi"
                    elif 'flask' in content.lower() or 'Flask' in content:
                        tech_stack = "flask"
                    elif 'django' in content.lower():
                        tech_stack = "django"
            except:
                pass
        
        # 检测端口（使用正确的方法）
        port_result = port_detector.detect_backend_port(backend_dir)
        port_config = None
        if port_result and port_result.port:
            port_config = PortConfig(
                port=port_result.port,
                detected_port=port_result.port,
                port_source=port_result.source,
                port_source_file=port_result.details,
                confidence=port_result.confidence
            )
        else:
            # 默认端口
            default_port = 8000
            port_config = PortConfig(
                port=default_port,
                port_source="默认端口",
                confidence=0.3
            )
        
        # 选择Python环境（优先选择Conda环境）
        python_env = None
        if self.available_python_envs:
            # 优先选择Conda环境
            conda_envs = [e for e in self.available_python_envs if e.is_conda]
            if conda_envs:
                python_env = conda_envs[0]
            else:
                python_env = self.available_python_envs[0]
        
        # 生成启动命令
        command = ""
        command_template = ""
        startup_filename = os.path.basename(startup_file)
        
        if tech_stack == "fastapi":
            # 尝试从启动文件中提取app变量名
            app_name = "main:app"
            if startup_filename != "main.py":
                app_name = f"{startup_filename[:-3]}:app"
            
            if python_env:
                command = f'"{python_env.path}" -m uvicorn {app_name} --reload --port {port_config.port}'
                command_template = '{python_env} -m uvicorn ' + app_name + ' --reload --port {port}'
            else:
                command = f'python -m uvicorn {app_name} --reload --port {port_config.port}'
                command_template = 'python -m uvicorn ' + app_name + ' --reload --port {port}'
        elif tech_stack == "flask":
            if python_env:
                command = f'"{python_env.path}" {startup_filename}'
                command_template = '{python_env} ' + startup_filename
            else:
                command = f'python {startup_filename}'
                command_template = 'python ' + startup_filename
        elif tech_stack == "django":
            if python_env:
                command = f'"{python_env.path}" manage.py runserver {port_config.port}'
                command_template = '{python_env} manage.py runserver {port}'
            else:
                command = f'python manage.py runserver {port_config.port}'
                command_template = 'python manage.py runserver {port}'
        else:
            if python_env:
                command = f'"{python_env.path}" {startup_filename}'
                command_template = '{python_env} ' + startup_filename
            else:
                command = f'python {startup_filename}'
                command_template = 'python ' + startup_filename
        
        return DetectedService(
            service_type="backend",
            name="后端服务",
            tech_stack=tech_stack,
            working_dir=backend_dir,
            startup_file=startup_file,
            command=command,
            command_template=command_template,
            port_config=port_config,
            python_env=python_env,
            confidence=0.85
        )
    
    def get_python_environments(self) -> List[PythonEnvironment]:
        """获取所有可用的Python环境"""
        return self.available_python_envs


# 全局实例
enhanced_detector = EnhancedProjectDetector()
