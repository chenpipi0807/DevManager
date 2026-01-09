"""深度端口检测器 - 从源码文件中精确读取端口配置"""
import os
import json
import re
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class PortDetectionResult:
    """端口检测结果"""
    port: Optional[int]
    source: str  # 端口来源：package.json, vite.config.js, .env, main.py等
    confidence: float  # 置信度 0-1
    env_var: Optional[str] = None  # 如果使用环境变量，记录变量名
    details: str = ""  # 详细信息


class PortDetector:
    """深度端口检测器"""
    
    def detect_frontend_port(self, project_path: str) -> PortDetectionResult:
        """检测前端项目端口（深入读取配置文件）"""
        
        # 1. 检查 package.json 中的 scripts
        pkg_result = self._check_package_json(project_path)
        if pkg_result and pkg_result.confidence > 0.7:
            return pkg_result
        
        # 2. 检查 vite.config.js/ts
        vite_result = self._check_vite_config(project_path)
        if vite_result and vite_result.confidence > 0.8:
            return vite_result
        
        # 3. 检查 .env 文件
        env_result = self._check_env_files(project_path)
        if env_result and env_result.confidence > 0.7:
            return env_result
        
        # 4. 检查 vue.config.js
        vue_result = self._check_vue_config(project_path)
        if vue_result and vue_result.confidence > 0.8:
            return vue_result
        
        # 5. 检查 webpack.config.js
        webpack_result = self._check_webpack_config(project_path)
        if webpack_result and webpack_result.confidence > 0.7:
            return webpack_result
        
        # 6. 检查 next.config.js
        next_result = self._check_next_config(project_path)
        if next_result and next_result.confidence > 0.8:
            return next_result
        
        # 返回最高置信度的结果或默认值
        results = [r for r in [pkg_result, vite_result, env_result, vue_result, webpack_result, next_result] if r]
        if results:
            return max(results, key=lambda x: x.confidence)
        
        return PortDetectionResult(
            port=None,
            source="default",
            confidence=0.0,
            details="未找到端口配置"
        )
    
    def detect_backend_port(self, project_path: str) -> PortDetectionResult:
        """检测后端项目端口（深入读取配置文件）"""
        
        # 1. 检查 Python 项目
        python_result = self._check_python_port(project_path)
        if python_result and python_result.confidence > 0.7:
            return python_result
        
        # 2. 检查 .env 文件
        env_result = self._check_env_files(project_path)
        if env_result and env_result.confidence > 0.7:
            return env_result
        
        # 3. 检查 Node.js 后端
        node_result = self._check_node_backend_port(project_path)
        if node_result and node_result.confidence > 0.7:
            return node_result
        
        # 返回最高置信度的结果
        results = [r for r in [python_result, env_result, node_result] if r]
        if results:
            return max(results, key=lambda x: x.confidence)
        
        return PortDetectionResult(
            port=None,
            source="default",
            confidence=0.0,
            details="未找到端口配置"
        )
    
    def _check_package_json(self, project_path: str) -> Optional[PortDetectionResult]:
        """检查 package.json 中的端口配置"""
        pkg_path = os.path.join(project_path, "package.json")
        if not os.path.exists(pkg_path):
            return None
        
        try:
            with open(pkg_path, 'r', encoding='utf-8') as f:
                pkg = json.load(f)
            
            scripts = pkg.get('scripts', {})
            
            # 检查 dev/start 脚本中的端口
            for script_name in ['dev', 'start', 'serve']:
                if script_name in scripts:
                    script = scripts[script_name]
                    
                    # 匹配 --port 3000, -p 3000, PORT=3000 等
                    patterns = [
                        r'--port[=\s]+(\d+)',
                        r'-p[=\s]+(\d+)',
                        r'PORT[=\s]+(\d+)',
                        r'port[=\s]+(\d+)',
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, script)
                        if match:
                            port = int(match.group(1))
                            return PortDetectionResult(
                                port=port,
                                source=f"package.json (scripts.{script_name})",
                                confidence=0.9,
                                details=f"从脚本中读取: {script}"
                            )
                    
                    # 检查环境变量引用
                    if 'PORT' in script or '$PORT' in script or '%PORT%' in script:
                        return PortDetectionResult(
                            port=None,
                            source=f"package.json (scripts.{script_name})",
                            confidence=0.6,
                            env_var="PORT",
                            details=f"使用环境变量 PORT: {script}"
                        )
            
            return None
        except Exception as e:
            return None
    
    def _check_vite_config(self, project_path: str) -> Optional[PortDetectionResult]:
        """检查 vite.config.js/ts 中的端口配置"""
        for config_file in ['vite.config.js', 'vite.config.ts', 'vite.config.mjs']:
            config_path = os.path.join(project_path, config_file)
            if not os.path.exists(config_path):
                continue
            
            try:
                with open(config_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # 匹配 server: { port: 3000 }
                patterns = [
                    r'server\s*:\s*\{[^}]*port\s*:\s*(\d+)',
                    r'port\s*:\s*(\d+)',
                    r'PORT\s*:\s*(\d+)',
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, content)
                    if match:
                        port = int(match.group(1))
                        return PortDetectionResult(
                            port=port,
                            source=config_file,
                            confidence=0.95,
                            details=f"从 Vite 配置文件读取"
                        )
                
                # 检查环境变量引用
                if 'process.env.PORT' in content or 'import.meta.env.PORT' in content:
                    return PortDetectionResult(
                        port=None,
                        source=config_file,
                        confidence=0.7,
                        env_var="PORT",
                        details="Vite 配置使用环境变量 PORT"
                    )
                
            except Exception as e:
                continue
        
        return None
    
    def _check_env_files(self, project_path: str) -> Optional[PortDetectionResult]:
        """检查 .env 文件中的端口配置"""
        env_files = ['.env', '.env.local', '.env.development', '.env.dev']
        
        for env_file in env_files:
            env_path = os.path.join(project_path, env_file)
            if not os.path.exists(env_path):
                continue
            
            try:
                with open(env_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # 匹配 PORT=3000, VITE_PORT=3000 等
                patterns = [
                    r'^PORT\s*=\s*(\d+)',
                    r'^VITE_PORT\s*=\s*(\d+)',
                    r'^REACT_APP_PORT\s*=\s*(\d+)',
                    r'^VUE_APP_PORT\s*=\s*(\d+)',
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, content, re.MULTILINE)
                    if match:
                        port = int(match.group(1))
                        return PortDetectionResult(
                            port=port,
                            source=env_file,
                            confidence=0.85,
                            details=f"从环境变量文件读取"
                        )
                
            except Exception as e:
                continue
        
        return None
    
    def _check_vue_config(self, project_path: str) -> Optional[PortDetectionResult]:
        """检查 vue.config.js 中的端口配置"""
        config_path = os.path.join(project_path, "vue.config.js")
        if not os.path.exists(config_path):
            return None
        
        try:
            with open(config_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # 匹配 devServer: { port: 8080 }
            patterns = [
                r'devServer\s*:\s*\{[^}]*port\s*:\s*(\d+)',
                r'port\s*:\s*(\d+)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, content)
                if match:
                    port = int(match.group(1))
                    return PortDetectionResult(
                        port=port,
                        source="vue.config.js",
                        confidence=0.9,
                        details="从 Vue 配置文件读取"
                    )
            
        except Exception as e:
            pass
        
        return None
    
    def _check_webpack_config(self, project_path: str) -> Optional[PortDetectionResult]:
        """检查 webpack.config.js 中的端口配置"""
        config_path = os.path.join(project_path, "webpack.config.js")
        if not os.path.exists(config_path):
            return None
        
        try:
            with open(config_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # 匹配 devServer: { port: 3000 }
            match = re.search(r'devServer\s*:\s*\{[^}]*port\s*:\s*(\d+)', content)
            if match:
                port = int(match.group(1))
                return PortDetectionResult(
                    port=port,
                    source="webpack.config.js",
                    confidence=0.9,
                    details="从 Webpack 配置文件读取"
                )
            
        except Exception as e:
            pass
        
        return None
    
    def _check_next_config(self, project_path: str) -> Optional[PortDetectionResult]:
        """检查 next.config.js 中的端口配置"""
        config_path = os.path.join(project_path, "next.config.js")
        if not os.path.exists(config_path):
            return None
        
        try:
            with open(config_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Next.js 通常通过环境变量设置端口
            if 'PORT' in content or 'process.env.PORT' in content:
                return PortDetectionResult(
                    port=None,
                    source="next.config.js",
                    confidence=0.7,
                    env_var="PORT",
                    details="Next.js 使用环境变量 PORT"
                )
            
        except Exception as e:
            pass
        
        return None
    
    def _check_python_port(self, project_path: str) -> Optional[PortDetectionResult]:
        """检查 Python 项目中的端口配置"""
        
        # 检查常见的 Python 入口文件
        entry_files = ['main.py', 'app.py', 'run.py', 'server.py']
        
        for entry_file in entry_files:
            file_path = os.path.join(project_path, entry_file)
            if not os.path.exists(file_path):
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # 匹配各种端口定义方式
                patterns = [
                    # uvicorn.run(app, host="0.0.0.0", port=8000)
                    r'uvicorn\.run\([^)]*port\s*=\s*(\d+)',
                    # app.run(port=5000)
                    r'\.run\([^)]*port\s*=\s*(\d+)',
                    # PORT = 8000
                    r'^PORT\s*=\s*(\d+)',
                    # port = 8000
                    r'^port\s*=\s*(\d+)',
                    # --port 8000 (命令行参数)
                    r'--port[=\s]+(\d+)',
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, content, re.MULTILINE | re.IGNORECASE)
                    if match:
                        port = int(match.group(1))
                        return PortDetectionResult(
                            port=port,
                            source=entry_file,
                            confidence=0.9,
                            details=f"从 Python 源码读取"
                        )
                
                # 检查环境变量引用
                if 'os.environ' in content or 'os.getenv' in content:
                    env_patterns = [
                        r'os\.environ(?:\[|\.get\()\s*["\']PORT["\']',
                        r'os\.getenv\(\s*["\']PORT["\']',
                    ]
                    for pattern in env_patterns:
                        if re.search(pattern, content):
                            return PortDetectionResult(
                                port=None,
                                source=entry_file,
                                confidence=0.75,
                                env_var="PORT",
                                details=f"Python 代码使用环境变量 PORT"
                            )
                
            except Exception as e:
                continue
        
        return None
    
    def _check_node_backend_port(self, project_path: str) -> Optional[PortDetectionResult]:
        """检查 Node.js 后端项目的端口配置"""
        
        # 检查常见的入口文件
        entry_files = ['server.js', 'app.js', 'index.js', 'src/server.js', 'src/app.js', 'src/index.js']
        
        for entry_file in entry_files:
            file_path = os.path.join(project_path, entry_file)
            if not os.path.exists(file_path):
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # 匹配端口定义
                patterns = [
                    # const PORT = 3000
                    r'(?:const|let|var)\s+PORT\s*=\s*(\d+)',
                    # app.listen(3000)
                    r'\.listen\(\s*(\d+)',
                    # port: 3000
                    r'port\s*:\s*(\d+)',
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, content)
                    if match:
                        port = int(match.group(1))
                        return PortDetectionResult(
                            port=port,
                            source=entry_file,
                            confidence=0.85,
                            details="从 Node.js 源码读取"
                        )
                
                # 检查环境变量引用
                if 'process.env.PORT' in content:
                    return PortDetectionResult(
                        port=None,
                        source=entry_file,
                        confidence=0.7,
                        env_var="PORT",
                        details="Node.js 代码使用环境变量 PORT"
                    )
                
            except Exception as e:
                continue
        
        return None
    
    def detect_env_port_override(self, command: str) -> Optional[Tuple[str, int]]:
        """检测命令中的环境变量端口覆盖
        
        返回: (环境变量名, 端口号) 或 None
        例如: $env:PORT=3764; npm start -> ("PORT", 3764)
        """
        
        # PowerShell 风格: $env:PORT=3764
        match = re.search(r'\$env:(\w+)\s*=\s*(\d+)', command)
        if match:
            return (match.group(1), int(match.group(2)))
        
        # Bash 风格: PORT=3764 npm start
        match = re.search(r'^(\w+)=(\d+)\s+', command)
        if match:
            return (match.group(1), int(match.group(2)))
        
        # 命令行参数: --port 3764
        match = re.search(r'--port[=\s]+(\d+)', command)
        if match:
            return ("PORT", int(match.group(1)))
        
        # 命令行参数: -p 3764
        match = re.search(r'-p[=\s]+(\d+)', command)
        if match:
            return ("PORT", int(match.group(1)))
        
        return None


# 全局实例
port_detector = PortDetector()
