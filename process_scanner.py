"""进程扫描器 - 检测系统中运行的开发相关进程"""
import subprocess
import os
from typing import List, Dict, Optional
from dataclasses import dataclass

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


@dataclass
class ExternalProcess:
    """外部进程信息"""
    pid: int
    name: str  # 进程名 (cmd.exe, powershell.exe, python.exe, node.exe 等)
    cwd: str  # 工作目录
    command_line: str  # 完整命令行
    matched_project_id: Optional[str] = None  # 匹配到的项目ID
    matched_service: Optional[str] = None  # 匹配到的服务类型


class ProcessScanner:
    """进程扫描器"""

    # 要扫描的进程类型
    TARGET_PROCESSES = [
        "cmd.exe",
        "powershell.exe",
        "pwsh.exe",  # PowerShell Core
        "python.exe",
        "pythonw.exe",
        "node.exe",
        "npm",
        "java.exe",
        "go.exe",
        "uvicorn",
        "gunicorn",
        "flask",
        "django",
    ]

    def __init__(self):
        pass

    def scan_processes(self) -> List[ExternalProcess]:
        """扫描系统中运行的开发相关进程"""
        if HAS_PSUTIL:
            return self._scan_with_psutil()
        return self._scan_with_powershell()

    def _scan_with_psutil(self) -> List[ExternalProcess]:
        """使用 psutil 扫描进程（更准确地获取工作目录）"""
        processes = []
        current_pid = os.getpid()

        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cwd', 'exe']):
                try:
                    info = proc.info
                    pid = info['pid']
                    name = info['name'] or ''

                    # 跳过当前进程
                    if pid == current_pid:
                        continue

                    # 检查是否是目标进程
                    name_lower = name.lower()
                    cmdline = info.get('cmdline') or []
                    cmdline_str = ' '.join(cmdline) if cmdline else ''
                    cmdline_lower = cmdline_str.lower()

                    is_target = any(
                        target.lower() in name_lower or target.lower() in cmdline_lower
                        for target in self.TARGET_PROCESSES
                    )

                    if not is_target:
                        continue

                    # 获取工作目录
                    cwd = ''
                    try:
                        cwd = info.get('cwd') or proc.cwd() or ''
                    except (psutil.AccessDenied, psutil.NoSuchProcess):
                        # 无权限时尝试从命令行推断
                        if info.get('exe'):
                            cwd = os.path.dirname(info['exe'])

                    ext_proc = ExternalProcess(
                        pid=pid,
                        name=name,
                        cwd=cwd,
                        command_line=cmdline_str
                    )
                    processes.append(ext_proc)

                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue

        except Exception as e:
            print(f"psutil 扫描失败: {e}")

        return processes

    def _scan_with_powershell(self) -> List[ExternalProcess]:
        """使用 PowerShell 扫描进程（备用方案）"""
        processes = []

        try:
            ps_script = '''
            Get-CimInstance Win32_Process | Where-Object {
                $_.Name -match 'cmd|powershell|pwsh|python|node|npm|java|go'
            } | ForEach-Object {
                $proc = $_
                try {
                    $cwd = ""
                    if ($proc.ExecutablePath) {
                        $cwd = Split-Path $proc.ExecutablePath -Parent
                    }
                } catch { $cwd = "" }
                
                [PSCustomObject]@{
                    PID = $proc.ProcessId
                    Name = $proc.Name
                    CommandLine = $proc.CommandLine
                    ExecutablePath = $proc.ExecutablePath
                    CWD = $cwd
                } | ConvertTo-Json -Compress
            }
            '''

            result = subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0 and result.stdout.strip():
                import json
                for line in result.stdout.strip().split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        if data['PID'] == os.getpid():
                            continue
                        
                        proc = ExternalProcess(
                            pid=data['PID'],
                            name=data['Name'] or '',
                            cwd=self._extract_cwd(data),
                            command_line=data['CommandLine'] or ''
                        )
                        processes.append(proc)
                    except (json.JSONDecodeError, KeyError):
                        continue

        except Exception as e:
            print(f"PowerShell 扫描失败: {e}")

        return processes

    def _extract_cwd(self, data: dict) -> str:
        """从进程信息中提取工作目录"""
        # 优先使用 CWD
        if data.get('CWD'):
            return data['CWD']
        
        # 从命令行推断
        cmd = data.get('CommandLine', '')
        if cmd:
            # 尝试从命令行中找到路径
            parts = cmd.split()
            for part in parts:
                if os.path.isdir(part):
                    return part
        
        # 使用可执行文件路径
        if data.get('ExecutablePath'):
            return os.path.dirname(data['ExecutablePath'])
        
        return ''

    def scan_with_wmic(self) -> List[ExternalProcess]:
        """使用 WMIC 扫描（备用方案，更可靠获取命令行）"""
        processes = []

        try:
            result = subprocess.run(
                ['wmic', 'process', 'get', 'ProcessId,Name,CommandLine,ExecutablePath', '/format:csv'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines[1:]:  # 跳过标题行
                    parts = line.strip().split(',')
                    if len(parts) >= 4:
                        try:
                            name = parts[2] if len(parts) > 2 else ''
                            # 检查是否是目标进程
                            if not any(target.lower() in name.lower() for target in self.TARGET_PROCESSES):
                                continue
                            
                            pid = int(parts[3]) if parts[3].isdigit() else 0
                            if pid == os.getpid():
                                continue
                                
                            cmd_line = parts[1] if len(parts) > 1 else ''
                            exe_path = parts[4] if len(parts) > 4 else ''
                            
                            proc = ExternalProcess(
                                pid=pid,
                                name=name,
                                cwd=os.path.dirname(exe_path) if exe_path else '',
                                command_line=cmd_line
                            )
                            processes.append(proc)
                        except (ValueError, IndexError):
                            continue

        except Exception as e:
            print(f"WMIC 扫描失败: {e}")

        return processes

    def match_to_projects(self, processes: List[ExternalProcess], projects: list) -> List[ExternalProcess]:
        """将进程匹配到项目"""
        for proc in processes:
            if not proc.cwd and not proc.command_line:
                continue

            for project in projects:
                project_path = project.path.lower().replace('/', '\\')
                
                # 检查工作目录是否在项目路径下
                proc_cwd = proc.cwd.lower().replace('/', '\\')
                proc_cmd = proc.command_line.lower().replace('/', '\\')

                if project_path in proc_cwd or project_path in proc_cmd:
                    proc.matched_project_id = project.id
                    
                    # 尝试判断是前端还是后端
                    if 'node' in proc.name.lower() or 'npm' in proc.command_line.lower():
                        proc.matched_service = 'frontend'
                    elif 'python' in proc.name.lower():
                        proc.matched_service = 'backend'
                    else:
                        proc.matched_service = 'unknown'
                    break

        return processes

    def get_process_cwd_via_handle(self, pid: int) -> Optional[str]:
        """通过进程句柄获取工作目录（需要 psutil）"""
        try:
            import psutil
            proc = psutil.Process(pid)
            return proc.cwd()
        except:
            return None


# 全局单例
process_scanner = ProcessScanner()


def scan_and_match(projects: list) -> List[ExternalProcess]:
    """扫描并匹配进程到项目"""
    processes = process_scanner.scan_processes()
    if not processes:
        # 备用方案
        processes = process_scanner.scan_with_wmic()
    return process_scanner.match_to_projects(processes, projects)
