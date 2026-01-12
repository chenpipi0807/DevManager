"""进程管理器 - 负责服务的启停和日志捕获"""
import subprocess
import threading
import os
import signal
from typing import Dict, List, Callable, Optional
from collections import deque
from dataclasses import dataclass


@dataclass
class ProcessInfo:
    """进程信息"""
    process: subprocess.Popen
    thread: threading.Thread
    logs: deque  # 使用 deque 限制日志行数


class ProcessManager:
    """进程管理器"""

    MAX_LOG_LINES = 500  # 最大日志行数

    def __init__(self):
        self.processes: Dict[str, ProcessInfo] = {}
        self.log_callbacks: Dict[str, List[Callable[[str], None]]] = {}
        self._lock = threading.Lock()

    def _get_key(self, project_id: str, service: str) -> str:
        """生成进程唯一标识"""
        return f"{project_id}:{service}"

    def start_service(
        self,
        project_id: str,
        service: str,
        command: str,
        cwd: str,
        env: Optional[Dict[str, str]] = None
    ) -> bool:
        """启动服务"""
        key = self._get_key(project_id, service)

        # 检查是否已在运行
        if self.is_running(project_id, service):
            return True

        # 合并环境变量
        full_env = os.environ.copy()
        if env:
            full_env.update(env)

        try:
            logs = deque(maxlen=self.MAX_LOG_LINES)
            
            # 记录启动信息
            import datetime
            startup_log = f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 启动命令: {command}"
            logs.append(startup_log)
            self._notify_log(key, startup_log)
            
            cwd_log = f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 工作目录: {cwd}"
            logs.append(cwd_log)
            self._notify_log(key, cwd_log)
            
            popen_command = command
            if os.name == 'nt':
                stripped = command.lstrip()
                if stripped.startswith('&'):
                    popen_command = stripped[1:].lstrip()

            # 启动进程 - 使用无缓冲模式
            process = subprocess.Popen(
                popen_command,
                shell=True,
                cwd=cwd,
                env=full_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=0,  # 无缓冲，立即捕获输出
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            )

            # 创建日志读取线程
            thread = threading.Thread(
                target=self._read_output,
                args=(key, process, logs),
                daemon=True
            )
            thread.start()

            with self._lock:
                self.processes[key] = ProcessInfo(process, thread, logs)

            return True

        except Exception as e:
            self._notify_log(key, f"[错误] 启动失败: {e}")
            return False

    def stop_service(self, project_id: str, service: str) -> bool:
        """停止服务"""
        key = self._get_key(project_id, service)

        with self._lock:
            if key not in self.processes:
                return True

            info = self.processes[key]
            process = info.process

        try:
            if os.name == 'nt':
                # Windows: 使用 taskkill 终止进程树
                subprocess.run(
                    f'taskkill /F /T /PID {process.pid}',
                    shell=True,
                    capture_output=True
                )
            else:
                # Unix: 发送 SIGTERM
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)

            # 等待进程结束
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

        except Exception as e:
            self._notify_log(key, f"[警告] 停止时出错: {e}")

        with self._lock:
            if key in self.processes:
                del self.processes[key]

        self._notify_log(key, "[系统] 服务已停止")
        return True

    def is_running(self, project_id: str, service: str) -> bool:
        """检查服务是否运行中"""
        key = self._get_key(project_id, service)

        with self._lock:
            if key not in self.processes:
                return False
            return self.processes[key].process.poll() is None

    def get_logs(self, project_id: str, service: str) -> List[str]:
        """获取服务日志"""
        key = self._get_key(project_id, service)

        with self._lock:
            if key in self.processes:
                return list(self.processes[key].logs)
        return []

    def add_log_callback(self, project_id: str, service: str, callback: Callable[[str], None]):
        """添加日志回调"""
        key = self._get_key(project_id, service)

        with self._lock:
            if key not in self.log_callbacks:
                self.log_callbacks[key] = []
            self.log_callbacks[key].append(callback)

    def remove_log_callback(self, project_id: str, service: str, callback: Callable[[str], None]):
        """移除日志回调"""
        key = self._get_key(project_id, service)

        with self._lock:
            if key in self.log_callbacks:
                try:
                    self.log_callbacks[key].remove(callback)
                except ValueError:
                    pass

    def _read_output(self, key: str, process: subprocess.Popen, logs: deque):
        """读取进程输出"""
        try:
            for line in iter(process.stdout.readline, ''):
                if not line:
                    break
                line = line.rstrip('\n\r')
                logs.append(line)
                self._notify_log(key, line)
        except Exception:
            pass
        finally:
            if process.stdout:
                process.stdout.close()

    def _notify_log(self, key: str, line: str):
        """通知日志回调"""
        with self._lock:
            callbacks = self.log_callbacks.get(key, []).copy()

        for callback in callbacks:
            try:
                callback(line)
            except Exception:
                pass

    def stop_all(self):
        """停止所有服务"""
        keys = list(self.processes.keys())
        for key in keys:
            parts = key.split(":", 1)
            if len(parts) == 2:
                self.stop_service(parts[0], parts[1])


# 全局单例
process_manager = ProcessManager()
