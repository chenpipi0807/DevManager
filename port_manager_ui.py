"""端口管理器UI组件"""
import customtkinter as ctk
from tkinter import messagebox
from typing import List
from models import Project
from port_manager import port_manager


class PortManagerDialog(ctk.CTkToplevel):
    """端口管理器对话框"""

    def __init__(self, master, projects: List[Project]):
        super().__init__(master)
        self.projects = projects

        self.title("端口管理器")
        self.geometry("1000x700")
        self.configure(fg_color="#FAFAFA")

        self.transient(master)
        self.grab_set()

        # 创建标签页
        self.tabview = ctk.CTkTabview(self, fg_color="#FFFFFF")
        self.tabview.pack(fill="both", expand=True, padx=20, pady=20)

        # 添加标签页
        self.tabview.add("运行中端口")
        self.tabview.add("潜在冲突")
        self.tabview.add("Python环境")

        # 初始化各个标签页
        self._init_running_tab()
        self._init_conflict_tab()
        self._init_python_env_tab()

    def _init_running_tab(self):
        """初始化运行中端口标签页"""
        tab = self.tabview.tab("运行中端口")

        # 顶部说明
        info_frame = ctk.CTkFrame(tab, fg_color="#FFFFFF", corner_radius=8, border_width=1, border_color="#E5E5E5")
        info_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            info_frame,
            text="当前运行中的端口",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#000000"
        ).pack(anchor="w", padx=15, pady=(10, 5))

        ctk.CTkLabel(
            info_frame,
            text="显示系统中正在运行的开发服务端口 (3000-9999)",
            text_color="#8E8E93",
            font=ctk.CTkFont(size=12)
        ).pack(anchor="w", padx=15, pady=(0, 10))

        # 刷新按钮
        btn_frame = ctk.CTkFrame(tab, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkButton(
            btn_frame,
            text="刷新",
            width=100,
            fg_color="#000000",
            hover_color="#333333",
            text_color="#FFFFFF",
            command=self._show_running_ports
        ).pack(side="left", padx=10)

        # 端口列表
        self.running_scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        self.running_scroll.pack(fill="both", expand=True, padx=10, pady=10)

        # 显示提示信息，不自动加载（性能优化）
        hint_label = ctk.CTkLabel(
            self.running_scroll,
            text="点击上方「刷新」按钮查看运行中的端口",
            text_color="#8E8E93",
            font=ctk.CTkFont(size=13)
        )
        hint_label.pack(pady=50)

    def _show_running_ports(self):
        """显示当前运行中的端口"""
        import psutil
        
        # 清空
        for widget in self.running_scroll.winfo_children():
            widget.destroy()
        
        running_ports = []
        
        # 获取所有TCP连接
        try:
            connections = psutil.net_connections(kind='inet')
            port_info = {}
            
            for conn in connections:
                if conn.status == 'LISTEN' and conn.laddr:
                    port = conn.laddr.port
                    # 只显示常用开发端口范围
                    if 3000 <= port <= 9999:
                        # 获取进程信息
                        process_name = "未知进程"
                        pid = conn.pid
                        try:
                            if pid:
                                proc = psutil.Process(pid)
                                process_name = proc.name()
                        except:
                            pass
                        
                        port_info[port] = {
                            'pid': pid,
                            'process': process_name
                        }
            
            # 检查哪些是我们管理的项目的端口
            allocations = port_manager.get_all_allocations()
            managed_ports = {alloc.port: alloc for alloc in allocations}
            
            for port in sorted(port_info.keys()):
                info = port_info[port]
                if port in managed_ports:
                    alloc = managed_ports[port]
                    running_ports.append({
                        'port': port,
                        'project': alloc.project_name,
                        'service': alloc.service_name,
                        'managed': True,
                        'pid': info['pid'],
                        'process': info['process']
                    })
                else:
                    running_ports.append({
                        'port': port,
                        'project': '未知服务',
                        'service': '',
                        'managed': False,
                        'pid': info['pid'],
                        'process': info['process']
                    })
            
            if not running_ports:
                ctk.CTkLabel(
                    self.running_scroll,
                    text="当前没有运行中的开发服务端口 (3000-9999)",
                    text_color="#8E8E93",
                    font=ctk.CTkFont(size=14)
                ).pack(pady=30)
                return
            
            # 显示运行中的端口
            for item in running_ports:
                card = ctk.CTkFrame(self.running_scroll, fg_color="#FFFFFF", corner_radius=8, border_width=1, border_color="#E5E5E5")
                card.pack(fill="x", pady=(0, 8))
                
                header = ctk.CTkFrame(card, fg_color="transparent")
                header.pack(fill="x", padx=12, pady=(10, 5))
                
                ctk.CTkLabel(
                    header,
                    text=f":{item['port']}",
                    font=ctk.CTkFont(size=16, weight="bold"),
                    text_color="#000000"
                ).pack(side="left")
                
                status_label = ctk.CTkLabel(
                    header,
                    text="DevManager管理" if item['managed'] else "外部服务",
                    font=ctk.CTkFont(size=10),
                    text_color="#FFFFFF",
                    fg_color="#000000" if item['managed'] else "#666666",
                    corner_radius=4,
                    padx=8,
                    pady=2
                )
                status_label.pack(side="left", padx=10)
                
                # PID标签
                if item.get('pid'):
                    ctk.CTkLabel(
                        header,
                        text=f"PID: {item['pid']}",
                        font=ctk.CTkFont(size=9),
                        text_color="#8E8E93"
                    ).pack(side="right")
                
                # 项目信息
                project_text = f"{item['project']}" if not item['service'] else f"{item['project']} / {item['service']}"
                ctk.CTkLabel(
                    card,
                    text=project_text,
                    text_color="#000000",
                    font=ctk.CTkFont(size=12)
                ).pack(anchor="w", padx=12, pady=(0, 2))
                
                # 进程信息
                if item.get('process'):
                    ctk.CTkLabel(
                        card,
                        text=f"进程: {item['process']}",
                        text_color="#8E8E93",
                        font=ctk.CTkFont(size=10)
                    ).pack(anchor="w", padx=12, pady=(0, 10))
                
        except Exception as e:
            ctk.CTkLabel(
                self.running_scroll,
                text=f"检测失败: {e}",
                text_color="#000000",
                font=ctk.CTkFont(size=14)
            ).pack(pady=30)

    def _init_conflict_tab(self):
        """初始化潜在冲突标签页"""
        tab = self.tabview.tab("潜在冲突")

        # 顶部说明
        info_frame = ctk.CTkFrame(tab, fg_color="#FFFFFF", corner_radius=8, border_width=1, border_color="#E5E5E5")
        info_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            info_frame,
            text="潜在端口冲突",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#000000"
        ).pack(anchor="w", padx=15, pady=(10, 5))

        ctk.CTkLabel(
            info_frame,
            text="检测多个项目配置了相同端口的情况（可能导致启动冲突）",
            text_color="#8E8E93",
            font=ctk.CTkFont(size=12)
        ).pack(anchor="w", padx=15, pady=(0, 10))

        # 检测按钮
        btn_frame = ctk.CTkFrame(tab, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkButton(
            btn_frame,
            text="检测冲突",
            width=100,
            fg_color="#000000",
            hover_color="#333333",
            text_color="#FFFFFF",
            command=self._check_conflicts
        ).pack(side="left")

        self.conflict_status = ctk.CTkLabel(
            btn_frame,
            text="",
            text_color="#8E8E93"
        )
        self.conflict_status.pack(side="left", padx=15)

        # 冲突列表
        self.conflict_scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        self.conflict_scroll.pack(fill="both", expand=True, padx=10, pady=10)

        # 显示提示信息，不自动加载
        hint_label = ctk.CTkLabel(
            self.conflict_scroll,
            text="点击上方「检测冲突」按钮开始检测",
            text_color="#8E8E93",
            font=ctk.CTkFont(size=13)
        )
        hint_label.pack(pady=50)

    def _check_conflicts(self):
        """检查端口冲突"""
        # 清空
        for widget in self.conflict_scroll.winfo_children():
            widget.destroy()

        conflicts = port_manager.check_conflicts(self.projects)

        if not conflicts:
            self.conflict_status.configure(text="✅ 未发现端口冲突", text_color="#000000")
            ctk.CTkLabel(
                self.conflict_scroll,
                text="所有端口配置正常，未发现冲突",
                text_color="#000000",
                font=ctk.CTkFont(size=14)
            ).pack(pady=30)
            return

        self.conflict_status.configure(
            text=f"⚠️ 发现 {len(conflicts)} 个端口冲突",
            text_color="#000000"
        )

        # 显示冲突
        for conflict in conflicts:
            card = ctk.CTkFrame(self.conflict_scroll, fg_color="#FFFFFF", corner_radius=8, border_width=1, border_color="#E5E5E5")
            card.pack(fill="x", pady=(0, 10))

            # 端口号
            header = ctk.CTkFrame(card, fg_color="transparent")
            header.pack(fill="x", padx=12, pady=(10, 5))

            ctk.CTkLabel(
                header,
                text=f"端口 {conflict['port']} 冲突",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color="#000000"
            ).pack(side="left")

            ctk.CTkLabel(
                header,
                text=f"{len(conflict['users'])} 个服务",
                text_color="#000000",
                font=ctk.CTkFont(size=11)
            ).pack(side="right")

            # 冲突的服务列表
            for i, user in enumerate(conflict['users'], 1):
                service_frame = ctk.CTkFrame(card, fg_color="#F5F5F5", corner_radius=4)
                service_frame.pack(fill="x", padx=12, pady=(0, 8))

                ctk.CTkLabel(
                    service_frame,
                    text=f"{i}. {user['project_name']} / {user['service_name']}",
                    font=ctk.CTkFont(size=12),
                    text_color="#000000"
                ).pack(anchor="w", padx=10, pady=(8, 2))

                ctk.CTkLabel(
                    service_frame,
                    text=f"命令: {user['command'][:60]}...",
                    text_color="#8E8E93",
                    font=ctk.CTkFont(size=10)
                ).pack(anchor="w", padx=10, pady=(0, 8))

    def _init_python_env_tab(self):
        """初始化Python环境标签页"""
        tab = self.tabview.tab("Python环境")

        # 顶部说明
        info_frame = ctk.CTkFrame(tab, fg_color="#FFFFFF", corner_radius=8, border_width=1, border_color="#E5E5E5")
        info_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            info_frame,
            text="Python环境检测",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#000000"
        ).pack(anchor="w", padx=15, pady=(10, 5))

        ctk.CTkLabel(
            info_frame,
            text="检测系统中所有可用的Python环境",
            text_color="#8E8E93",
            font=ctk.CTkFont(size=12)
        ).pack(anchor="w", padx=15, pady=(0, 10))

        # 刷新按钮
        btn_frame = ctk.CTkFrame(tab, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkButton(
            btn_frame,
            text="检测Python环境",
            width=130,
            fg_color="#000000",
            hover_color="#333333",
            text_color="#FFFFFF",
            command=self._detect_python_envs
        ).pack(side="left", padx=10)

        # Python环境列表
        self.python_scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        self.python_scroll.pack(fill="both", expand=True, padx=10, pady=10)

        # 显示提示信息，不自动加载（性能优化）
        hint_label = ctk.CTkLabel(
            self.python_scroll,
            text="点击上方按钮开始检测Python环境",
            text_color="#8E8E93",
            font=ctk.CTkFont(size=13)
        )
        hint_label.pack(pady=50)

    def _detect_python_envs(self):
        """检测Python环境"""
        import subprocess
        import os
        
        # 清空
        for widget in self.python_scroll.winfo_children():
            widget.destroy()
        
        python_envs = []
        
        # 检测常见的Python路径
        common_paths = [
            r"C:\Python*\python.exe",
            r"C:\Program Files\Python*\python.exe",
            r"C:\ProgramData\anaconda3\python.exe",
            r"C:\Users\*\anaconda3\python.exe",
            r"C:\Users\*\miniconda3\python.exe",
            r"C:\Users\*\AppData\Local\Programs\Python\Python*\python.exe",
        ]
        
        # 使用where命令查找python
        try:
            result = subprocess.run(
                ["where", "python"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line and os.path.exists(line):
                        python_envs.append(line.strip())
        except Exception:
            pass
        
        # 检查常见路径
        import glob
        for pattern in common_paths:
            try:
                for path in glob.glob(pattern, recursive=True):
                    if os.path.exists(path) and path not in python_envs:
                        python_envs.append(path)
            except Exception:
                pass
        
        # 检查conda环境
        try:
            result = subprocess.run(
                ["conda", "env", "list"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line and not line.startswith('#') and '*' not in line:
                        parts = line.split()
                        if len(parts) >= 2:
                            env_path = parts[-1]
                            python_path = os.path.join(env_path, 'python.exe')
                            if os.path.exists(python_path) and python_path not in python_envs:
                                python_envs.append(python_path)
        except Exception:
            pass
        
        if not python_envs:
            ctk.CTkLabel(
                self.python_scroll,
                text="未检测到Python环境",
                text_color="#8E8E93",
                font=ctk.CTkFont(size=14)
            ).pack(pady=30)
            return
        
        # 显示Python环境
        for i, python_path in enumerate(python_envs, 1):
            card = ctk.CTkFrame(self.python_scroll, fg_color="#FFFFFF", corner_radius=8, border_width=1, border_color="#E5E5E5")
            card.pack(fill="x", pady=(0, 8))
            
            header = ctk.CTkFrame(card, fg_color="transparent")
            header.pack(fill="x", padx=12, pady=(10, 5))
            
            # 获取Python版本
            version = "未知版本"
            try:
                result = subprocess.run(
                    [python_path, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=3
                )
                if result.returncode == 0:
                    version = result.stdout.strip() or result.stderr.strip()
            except Exception:
                pass
            
            ctk.CTkLabel(
                header,
                text=f"#{i} {version}",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color="#000000"
            ).pack(side="left")
            
            # 检查是否是conda环境
            is_conda = "anaconda" in python_path.lower() or "miniconda" in python_path.lower()
            if is_conda:
                ctk.CTkLabel(
                    header,
                    text="Conda",
                    font=ctk.CTkFont(size=10),
                    text_color="#FFFFFF",
                    fg_color="#000000",
                    corner_radius=4,
                    padx=8,
                    pady=2
                ).pack(side="left", padx=10)
            
            # 路径
            ctk.CTkLabel(
                card,
                text=f"路径: {python_path}",
                text_color="#8E8E93",
                font=ctk.CTkFont(size=11)
            ).pack(anchor="w", padx=12, pady=(0, 10))
