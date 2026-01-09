"""DevManager - 本地开发项目管理面板 (GUI版)"""
import customtkinter as ctk
from tkinter import messagebox, filedialog
import threading
import os
from typing import Optional, Dict, List
from enhanced_models import Project, ServiceConfig, enhanced_project_manager
from process_manager import process_manager
from process_scanner import scan_and_match, ExternalProcess
from project_detector import detect_project
from port_manager import port_manager
from port_manager_ui import PortManagerDialog
from port_detector import port_detector
from port_edit_dialog import PortEditDialog
from enhanced_project_form import EnhancedProjectFormDialog
from enhanced_logger import enhanced_logger

# 图标路径
ICON_PATH = os.path.join(os.path.dirname(__file__), "icon.ico")

# Windows 任务栏图标设置（必须在创建窗口前调用）
try:
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("DevManager.App")
except:
    pass

# 设置主题 - 极简主义黑白灰
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# 极简主义黑白灰配色方案（苹果/原研哉风格）
COLORS = {
    "bg_primary": "#FAFAFA",      # 主背景 - 极浅灰
    "bg_secondary": "#FFFFFF",    # 次级背景 - 纯白
    "bg_tertiary": "#FFFFFF",     # 卡片背景 - 纯白
    "bg_hover": "#F5F5F5",        # 悬停背景 - 浅灰
    "border": "#E5E5E5",          # 边框 - 淡灰
    "text_primary": "#000000",    # 主文本 - 纯黑
    "text_secondary": "#8E8E93",  # 次级文本 - 中灰
    "accent_blue": "#000000",     # 主色调 - 黑色
    "accent_green": "#000000",    # 成功 - 黑色
    "accent_orange": "#666666",   # 警告 - 深灰
    "accent_red": "#000000",      # 错误 - 黑色
    "status_running": "#000000",  # 运行中 - 黑色
    "status_stopped": "#C7C7CC",  # 已停止 - 浅灰
    "cta_blue": "#000000",        # CTA按钮 - 黑色
    "shadow": "0 1px 3px rgba(0,0,0,0.06)",  # 极简阴影
}


class ServiceFrame(ctk.CTkFrame):
    """单个服务控制组件"""

    def __init__(self, master, project: Project, service_key: str, service: ServiceConfig, **kwargs):
        super().__init__(master, **kwargs)
        self.project = project
        self.service_key = service_key
        self.service = service

        self.configure(fg_color=COLORS["bg_tertiary"], corner_radius=8, border_width=1, border_color=COLORS["border"])

        # 单行布局：名称 | 命令 | 端口 | 状态 | 按钮
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="x", padx=8, pady=6)

        # 左侧：服务类型图标 + 名称
        icon_text = "🔷" if service_key == "backend" else "🔶"
        service_type = "后端" if service_key == "backend" else "前端"
        
        icon_label = ctk.CTkLabel(
            content,
            text=icon_text,
            font=ctk.CTkFont(size=14),
            width=30
        )
        icon_label.pack(side="left")
        
        self.name_label = ctk.CTkLabel(
            content,
            text=f"{service_type} · {service.name or service_key}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["text_primary"],
            width=150,
            anchor="w"
        )
        self.name_label.pack(side="left", padx=(5, 0))

        # 命令（简短显示）
        cmd_short = service.command[:35] + "..." if len(service.command) > 35 else service.command
        cmd_label = ctk.CTkLabel(
            content,
            text=cmd_short,
            text_color=COLORS["text_secondary"],
            font=ctk.CTkFont(size=10, family="Consolas"),
            width=200,
            anchor="w"
        )
        cmd_label.pack(side="left", padx=(10, 0))

        # 端口（带背景标签）
        port = getattr(service, 'port', None) or (service.port_config.port if hasattr(service, 'port_config') and service.port_config else None)
        if port:
            port_frame = ctk.CTkFrame(
                content,
                fg_color=COLORS["bg_secondary"],
                corner_radius=4,
                height=20
            )
            port_frame.pack(side="left", padx=(10, 0))
            
            port_label = ctk.CTkLabel(
                port_frame,
                text=f":{port}",
                text_color=COLORS["accent_blue"],
                font=ctk.CTkFont(size=11, weight="bold", family="Consolas"),
                padx=8,
                pady=2
            )
            port_label.pack()
            
            # 如果是前端服务，显示完整访问链接
            if self.service_key == "frontend" or "frontend" in self.service.name.lower():
                url = f"http://localhost:{port}"
                url_label = ctk.CTkLabel(
                    content,
                    text=url,
                    text_color=COLORS["accent_blue"],
                    font=ctk.CTkFont(size=10, family="Consolas", underline=True),
                    cursor="hand2"
                )
                url_label.pack(side="left", padx=(5, 0))
                
                # 点击打开浏览器
                def open_browser(event=None):
                    import webbrowser
                    webbrowser.open(url)
                
                url_label.bind("<Button-1>", open_browser)

        # 右侧按钮组
        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.pack(side="right")

        # 状态标签（更现代的设计）
        self.status_label = ctk.CTkLabel(
            btn_frame,
            text="● 停止",
            text_color=COLORS["status_stopped"],
            font=ctk.CTkFont(size=11, weight="bold"),
            width=60
        )
        self.status_label.pack(side="left", padx=(0, 10))

        self.start_btn = ctk.CTkButton(
            btn_frame,
            text="▶ 启动",
            width=65,
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color=COLORS["accent_green"],
            hover_color="#1a9d6f",
            corner_radius=6,
            command=self.start_service
        )
        self.start_btn.pack(side="left", padx=(0, 6))

        self.stop_btn = ctk.CTkButton(
            btn_frame,
            text="■ 停止",
            width=65,
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color=COLORS["accent_red"],
            hover_color="#f5a397",
            corner_radius=6,
            command=self.stop_service
        )
        self.stop_btn.pack(side="left", padx=(0, 6))

        self.log_btn = ctk.CTkButton(
            btn_frame,
            text="📄 日志",
            width=65,
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color=COLORS["bg_secondary"],
            hover_color=COLORS["bg_hover"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=6,
            command=self.show_logs
        )
        self.log_btn.pack(side="left", padx=(0, 6))
        
        # 打开文件位置按钮
        self.open_folder_btn = ctk.CTkButton(
            btn_frame,
            text="📂",
            width=35,
            height=28,
            font=ctk.CTkFont(size=14),
            fg_color=COLORS["bg_secondary"],
            hover_color=COLORS["bg_hover"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=6,
            command=self.open_file_location
        )
        self.open_folder_btn.pack(side="left", padx=(0, 6))
        
        # 修改端口按钮
        if port:
            self.edit_port_btn = ctk.CTkButton(
                btn_frame,
                text="⚙️",
                width=35,
                height=28,
                font=ctk.CTkFont(size=14),
                fg_color=COLORS["bg_secondary"],
                hover_color=COLORS["bg_hover"],
                border_width=1,
                border_color=COLORS["border"],
                corner_radius=6,
                command=self.edit_port
            )
            self.edit_port_btn.pack(side="left")

        self.update_status()

    def start_service(self):
        """启动服务"""
        if not self.service.command:
            messagebox.showwarning("警告", "未配置启动命令")
            return

        # 检查端口冲突
        service_port = getattr(self.service, 'port', None) or (self.service.port_config.port if hasattr(self.service, 'port_config') and self.service.port_config else None)
        if service_port:
            if not port_manager.is_port_available(service_port):
                occupant = port_manager.get_port_occupant(service_port)
                if occupant:
                    msg = f"端口 {service_port} 已被占用\n\n进程: {occupant['name']} (PID: {occupant['pid']})\n命令: {occupant['cmdline'][:80]}...\n\n是否仍要启动？"
                    if not messagebox.askyesno("端口冲突警告", msg):
                        return
            
            # 更新端口使用记录
            tech_stack = port_manager.detect_tech_stack(self.service.command, self.service.working_dir if hasattr(self.service, 'working_dir') else self.project.path)
            port_manager.allocate_port(
                service_port,
                self.project.id,
                self.project.name,
                self.service_key,
                self.service.name or self.service_key,
                tech_stack
            )

        cwd = getattr(self.service, 'cwd', None) or getattr(self.service, 'working_dir', None) or self.project.path
        env_vars = getattr(self.service, 'env', None) or getattr(self.service, 'env_vars', {})
        success = process_manager.start_service(
            self.project.id,
            self.service_key,
            self.service.command,
            cwd,
            env_vars
        )
        if success:
            if service_port:
                port_manager.update_last_used(service_port)
            self.after(500, self.update_status)

    def stop_service(self):
        """停止服务"""
        process_manager.stop_service(self.project.id, self.service_key)
        self.after(500, self.update_status)

    def show_logs(self):
        """显示日志窗口"""
        LogWindow(self, self.project, self.service_key, self.service.name or self.service_key)
    
    def open_file_location(self):
        """打开启动文件所在位置"""
        import subprocess
        cwd = getattr(self.service, 'cwd', None) or getattr(self.service, 'working_dir', None) or self.project.path
        
        if os.path.exists(cwd):
            # Windows: 打开文件资源管理器
            subprocess.Popen(f'explorer "{cwd}"')
        else:
            messagebox.showwarning("警告", f"路径不存在: {cwd}")
    
    def edit_port(self):
        """修改端口"""
        PortEditDialog(self, self.project, self.service_key, self.service)

    def update_status(self):
        """更新状态显示"""
        running = process_manager.is_running(self.project.id, self.service_key)
        if running:
            self.status_label.configure(text="● 运行中", text_color=COLORS["status_running"])
            self.start_btn.configure(state="disabled", fg_color=COLORS["bg_secondary"])
            self.stop_btn.configure(state="normal")
        else:
            self.status_label.configure(text="● 已停止", text_color=COLORS["status_stopped"])
            self.start_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled", fg_color=COLORS["bg_secondary"])
    
    def refresh_display(self):
        """刷新显示（端口修改后调用）"""
        # 更新端口显示
        service_port = getattr(self.service, 'port', None) or (self.service.port_config.port if hasattr(self.service, 'port_config') and self.service.port_config else None)
        if service_port:
            for widget in self.winfo_children():
                widget.destroy()
            self.__init__(self.master, self.project, self.service_key, self.service)
            self.pack(fill="x", pady=(0, 8))


class LogWindow(ctk.CTkToplevel):
    """日志查看窗口"""

    def __init__(self, master, project: Project, service_key: str, service_name: str):
        super().__init__(master)
        self.project = project
        self.service_key = service_key
        self._is_alive = True  # 标记窗口是否存活

        self.title(f"日志 - {project.name} / {service_name}")
        self.geometry("800x500")
        self.configure(fg_color="#1a1a1a")

        # 日志文本框
        self.log_text = ctk.CTkTextbox(
            self,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color="#0d0d0d",
            text_color="#00ff00",
            corner_radius=8
        )
        self.log_text.pack(fill="both", expand=True, padx=10, pady=10)

        # 底部按钮
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkButton(
            btn_frame,
            text="清空",
            width=80,
            command=self.clear_logs
        ).pack(side="left")

        ctk.CTkButton(
            btn_frame,
            text="关闭",
            width=80,
            command=self.on_close
        ).pack(side="right")

        # 加载历史日志
        self.load_logs()

        # 注册日志回调
        self.log_callback = self.on_new_log
        process_manager.add_log_callback(self.project.id, self.service_key, self.log_callback)

    def load_logs(self):
        """加载历史日志"""
        logs = process_manager.get_logs(self.project.id, self.service_key)
        if logs:
            for line in logs:
                self.log_text.insert("end", line + "\n")
            self.log_text.see("end")

    def on_new_log(self, line: str):
        """新日志回调"""
        if self._is_alive:
            self.after(0, lambda: self._append_log(line))

    def _append_log(self, line: str):
        """追加日志（主线程）"""
        if not self._is_alive:
            return
        try:
            self.log_text.insert("end", line + "\n")
            self.log_text.see("end")
        except Exception:
            pass  # 窗口已销毁

    def clear_logs(self):
        """清空日志"""
        self.log_text.delete("1.0", "end")

    def on_close(self):
        """关闭窗口"""
        self._is_alive = False
        process_manager.remove_log_callback(self.project.id, self.service_key, self.log_callback)
        self.destroy()


class ProjectCard(ctk.CTkFrame):
    """项目卡片组件"""

    def __init__(self, master, project: Project, on_edit, on_delete, **kwargs):
        super().__init__(master, **kwargs)
        self.project = project
        self.on_edit = on_edit
        self.on_delete = on_delete

        self.configure(
            fg_color=COLORS["bg_tertiary"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"]
        )

        # 项目头部
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=(15, 10))

        # 项目名称和图标
        name_frame = ctk.CTkFrame(header, fg_color="transparent")
        name_frame.pack(side="left")
        
        project_icon = ctk.CTkLabel(
            name_frame,
            text="📁",
            font=ctk.CTkFont(size=20)
        )
        project_icon.pack(side="left", padx=(0, 8))
        
        name_label = ctk.CTkLabel(
            name_frame,
            text=project.name,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        name_label.pack(side="left")

        # 操作按钮
        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.pack(side="right")

        ctk.CTkButton(
            btn_frame,
            text="▶ 全部启动",
            width=95,
            height=32,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=COLORS["accent_green"],
            hover_color="#1a9d6f",
            corner_radius=6,
            command=self.start_all_services
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            btn_frame,
            text="■ 全部停止",
            width=95,
            height=32,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=COLORS["accent_orange"],
            hover_color="#d4a183",
            corner_radius=6,
            command=self.stop_all_services
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            btn_frame,
            text="✏️ 编辑",
            width=70,
            height=32,
            font=ctk.CTkFont(size=11),
            fg_color=COLORS["accent_blue"],
            hover_color="#0098ee",
            corner_radius=6,
            command=lambda: on_edit(project)
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            btn_frame,
            text="🗑️ 删除",
            width=70,
            height=32,
            font=ctk.CTkFont(size=11),
            fg_color=COLORS["accent_red"],
            hover_color="#f5a397",
            corner_radius=6,
            command=lambda: on_delete(project)
        ).pack(side="left")

        # 项目描述
        if project.description:
            desc_label = ctk.CTkLabel(
                self,
                text=project.description,
                text_color=COLORS["text_secondary"],
                font=ctk.CTkFont(size=12)
            )
            desc_label.pack(anchor="w", padx=15, pady=(0, 5))

        # 项目路径（带背景）
        path_frame = ctk.CTkFrame(
            self,
            fg_color=COLORS["bg_secondary"],
            corner_radius=6,
            height=28
        )
        path_frame.pack(fill="x", padx=15, pady=(5, 12))
        
        path_label = ctk.CTkLabel(
            path_frame,
            text=f"� {project.path}",
            text_color=COLORS["text_secondary"],
            font=ctk.CTkFont(size=10, family="Consolas"),
            anchor="w"
        )
        path_label.pack(fill="x", padx=10, pady=6)

        # 服务列表
        self.services_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.services_frame.pack(fill="x", padx=15, pady=(0, 15))

        self.service_widgets = []
        for key, service in project.services.items():
            if service.enabled:
                service_frame = ServiceFrame(self.services_frame, project, key, service)
                service_frame.pack(fill="x", pady=(0, 8))
                self.service_widgets.append(service_frame)

    def start_all_services(self):
        """启动所有服务"""
        # 按顺序启动：先后端，后前端
        services_order = ["backend", "frontend"]
        for service_key in services_order:
            service = self.project.services.get(service_key)
            if service and service.enabled and service.command:
                # 检查端口冲突
                service_port = getattr(service, 'port', None) or (service.port_config.port if hasattr(service, 'port_config') and service.port_config else None)
                if service_port and not port_manager.is_port_available(service_port):
                    occupant = port_manager.get_port_occupant(service_port)
                    if occupant:
                        msg = f"端口 {service_port} ({service.name}) 已被占用\n\n进程: {occupant['name']} (PID: {occupant['pid']})\n\n跳过此服务？"
                        if not messagebox.askyesno("端口冲突", msg):
                            continue
                
                # 启动服务
                cwd = getattr(service, 'cwd', None) or getattr(service, 'working_dir', None) or self.project.path
                env_vars = getattr(service, 'env', None) or getattr(service, 'env_vars', {})
                process_manager.start_service(
                    self.project.id,
                    service_key,
                    service.command,
                    cwd,
                    env_vars
                )
                
                # 更新端口记录
                if service_port:
                    tech_stack = port_manager.detect_tech_stack(service.command, cwd)
                    port_manager.allocate_port(
                        service_port,
                        self.project.id,
                        self.project.name,
                        service_key,
                        service.name or service_key,
                        tech_stack
                    )
        
        # 延迟更新UI
        self.after(500, self.update_all_status)

    def stop_all_services(self):
        """停止所有服务"""
        # 按相反顺序停止：先前端，后后端
        services_order = ["frontend", "backend"]
        for service_key in services_order:
            service = self.project.services.get(service_key)
            if service and service.enabled:
                process_manager.stop_service(self.project.id, service_key)
        
        # 延迟更新UI
        self.after(500, self.update_all_status)

    def update_all_status(self):
        """更新所有服务状态"""
        for widget in self.service_widgets:
            widget.update_status()


class ProjectFormDialog(ctk.CTkToplevel):
    """项目表单对话框"""

    def __init__(self, master, project: Optional[Project] = None, on_save=None):
        super().__init__(master)
        self.project = project
        self.on_save = on_save
        self.is_edit = project is not None

        self.title("编辑项目" if self.is_edit else "添加项目")
        self.geometry("600x700")
        self.configure(fg_color="#1a1a1a")

        # 使窗口模态
        self.transient(master)
        self.grab_set()

        # 滚动容器
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # 基本信息
        self._create_section("基本信息")

        ctk.CTkLabel(self.scroll_frame, text="项目名称 *").pack(anchor="w", pady=(10, 2))
        self.name_entry = ctk.CTkEntry(self.scroll_frame, width=400)
        self.name_entry.pack(anchor="w")

        ctk.CTkLabel(self.scroll_frame, text="项目描述").pack(anchor="w", pady=(10, 2))
        self.desc_entry = ctk.CTkEntry(self.scroll_frame, width=400)
        self.desc_entry.pack(anchor="w")

        ctk.CTkLabel(self.scroll_frame, text="项目路径 *").pack(anchor="w", pady=(10, 2))
        path_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        path_frame.pack(anchor="w")
        self.path_entry = ctk.CTkEntry(path_frame, width=340)
        self.path_entry.pack(side="left")
        ctk.CTkButton(
            path_frame,
            text="浏览",
            width=55,
            command=self.browse_path
        ).pack(side="left", padx=(5, 0))

        # 后端服务
        self._create_section("后端服务")
        self.backend_enabled = ctk.CTkCheckBox(self.scroll_frame, text="启用后端服务")
        self.backend_enabled.pack(anchor="w", pady=(10, 5))

        ctk.CTkLabel(self.scroll_frame, text="服务名称").pack(anchor="w", pady=(5, 2))
        self.backend_name = ctk.CTkEntry(self.scroll_frame, width=400, placeholder_text="后端服务")
        self.backend_name.pack(anchor="w")

        ctk.CTkLabel(self.scroll_frame, text="启动命令").pack(anchor="w", pady=(5, 2))
        self.backend_cmd = ctk.CTkEntry(self.scroll_frame, width=400, placeholder_text="C:\\ProgramData\\anaconda3\\python.exe main.py")
        self.backend_cmd.pack(anchor="w")

        ctk.CTkLabel(self.scroll_frame, text="工作目录 (留空则使用项目路径)").pack(anchor="w", pady=(5, 2))
        self.backend_cwd = ctk.CTkEntry(self.scroll_frame, width=400)
        self.backend_cwd.pack(anchor="w")

        port_label_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        port_label_frame.pack(anchor="w", pady=(5, 2))
        ctk.CTkLabel(port_label_frame, text="端口").pack(side="left")
        self.backend_port_hint = ctk.CTkLabel(
            port_label_frame,
            text="",
            text_color="#888888",
            font=ctk.CTkFont(size=10)
        )
        self.backend_port_hint.pack(side="left", padx=10)
        
        backend_port_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        backend_port_frame.pack(anchor="w")
        self.backend_port = ctk.CTkEntry(backend_port_frame, width=100, placeholder_text="8000")
        self.backend_port.pack(side="left")
        ctk.CTkButton(
            backend_port_frame,
            text="智能建议",
            width=80,
            height=24,
            fg_color="#6c757d",
            hover_color="#5a6268",
            command=lambda: self._suggest_port("backend")
        ).pack(side="left", padx=5)

        # 前端服务
        self._create_section("前端服务")
        self.frontend_enabled = ctk.CTkCheckBox(self.scroll_frame, text="启用前端服务")
        self.frontend_enabled.pack(anchor="w", pady=(10, 5))

        ctk.CTkLabel(self.scroll_frame, text="服务名称").pack(anchor="w", pady=(5, 2))
        self.frontend_name = ctk.CTkEntry(self.scroll_frame, width=400, placeholder_text="前端服务")
        self.frontend_name.pack(anchor="w")

        ctk.CTkLabel(self.scroll_frame, text="启动命令").pack(anchor="w", pady=(5, 2))
        self.frontend_cmd = ctk.CTkEntry(self.scroll_frame, width=400, placeholder_text="npm run dev")
        self.frontend_cmd.pack(anchor="w")

        ctk.CTkLabel(self.scroll_frame, text="工作目录 (留空则使用项目路径)").pack(anchor="w", pady=(5, 2))
        self.frontend_cwd = ctk.CTkEntry(self.scroll_frame, width=400)
        self.frontend_cwd.pack(anchor="w")

        port_label_frame2 = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        port_label_frame2.pack(anchor="w", pady=(5, 2))
        ctk.CTkLabel(port_label_frame2, text="端口").pack(side="left")
        self.frontend_port_hint = ctk.CTkLabel(
            port_label_frame2,
            text="",
            text_color="#888888",
            font=ctk.CTkFont(size=10)
        )
        self.frontend_port_hint.pack(side="left", padx=10)
        
        frontend_port_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        frontend_port_frame.pack(anchor="w")
        self.frontend_port = ctk.CTkEntry(frontend_port_frame, width=100, placeholder_text="5173")
        self.frontend_port.pack(side="left")
        ctk.CTkButton(
            frontend_port_frame,
            text="智能建议",
            width=80,
            height=24,
            fg_color="#6c757d",
            hover_color="#5a6268",
            command=lambda: self._suggest_port("frontend")
        ).pack(side="left", padx=5)

        # 底部按钮
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=20)

        ctk.CTkButton(
            btn_frame,
            text="取消",
            width=100,
            fg_color="#6c757d",
            hover_color="#5a6268",
            command=self.destroy
        ).pack(side="right")

        ctk.CTkButton(
            btn_frame,
            text="保存",
            width=100,
            fg_color="#28a745",
            hover_color="#218838",
            command=self.save
        ).pack(side="right", padx=(0, 10))

        # 填充数据
        if self.is_edit:
            self._fill_data()

    def _create_section(self, title: str):
        """创建分区标题"""
        label = ctk.CTkLabel(
            self.scroll_frame,
            text=title,
            font=ctk.CTkFont(size=16, weight="bold")
        )
        label.pack(anchor="w", pady=(20, 0))
        separator = ctk.CTkFrame(self.scroll_frame, height=2, fg_color="#333333")
        separator.pack(fill="x", pady=(5, 0))

    def _fill_data(self):
        """填充编辑数据"""
        p = self.project
        self.name_entry.insert(0, p.name)
        self.desc_entry.insert(0, p.description)
        self.path_entry.insert(0, p.path)

        # 后端服务
        backend = p.services.get("backend")
        if backend:
            if backend.enabled:
                self.backend_enabled.select()
            self.backend_name.insert(0, backend.name)
            self.backend_cmd.insert(0, backend.command)
            self.backend_cwd.insert(0, backend.cwd)
            if backend.port:
                self.backend_port.insert(0, str(backend.port))

        # 前端服务
        frontend = p.services.get("frontend")
        if frontend:
            if frontend.enabled:
                self.frontend_enabled.select()
            self.frontend_name.insert(0, frontend.name)
            self.frontend_cmd.insert(0, frontend.command)
            self.frontend_cwd.insert(0, frontend.cwd)
            if frontend.port:
                self.frontend_port.insert(0, str(frontend.port))

    def browse_path(self):
        """浏览文件夹并自动检测项目"""
        path = filedialog.askdirectory()
        if path:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, path)
            
            # 自动检测项目结构
            self._auto_detect(path)

    def _auto_detect(self, path: str):
        """自动检测项目结构并填充表单"""
        try:
            detected = detect_project(path)
            
            # 填充项目名称（如果为空）
            if not self.name_entry.get().strip():
                self.name_entry.delete(0, "end")
                self.name_entry.insert(0, detected.name)

            # 填充后端服务
            if detected.backend:
                self.backend_enabled.select()
                self._clear_and_insert(self.backend_name, detected.backend.name)
                self._clear_and_insert(self.backend_cmd, detected.backend.command)
                self._clear_and_insert(self.backend_cwd, detected.backend.cwd)
                if detected.backend.port:
                    self._clear_and_insert(self.backend_port, str(detected.backend.port))
                    # 显示端口来源
                    if detected.backend.port_source:
                        confidence_text = f"{detected.backend.port_confidence*100:.0f}%"
                        hint_text = f"来源: {detected.backend.port_source} (置信度: {confidence_text})"
                        if detected.backend.env_var:
                            hint_text += f" [环境变量: {detected.backend.env_var}]"
                        self.backend_port_hint.configure(text=hint_text, text_color="#4ec9b0")
            
            # 填充前端服务
            if detected.frontend:
                self.frontend_enabled.select()
                self._clear_and_insert(self.frontend_name, detected.frontend.name)
                self._clear_and_insert(self.frontend_cmd, detected.frontend.command)
                self._clear_and_insert(self.frontend_cwd, detected.frontend.cwd)
                if detected.frontend.port:
                    self._clear_and_insert(self.frontend_port, str(detected.frontend.port))
                    # 显示端口来源
                    if detected.frontend.port_source:
                        confidence_text = f"{detected.frontend.port_confidence*100:.0f}%"
                        hint_text = f"来源: {detected.frontend.port_source} (置信度: {confidence_text})"
                        if detected.frontend.env_var:
                            hint_text += f" [环境变量: {detected.frontend.env_var}]"
                        self.frontend_port_hint.configure(text=hint_text, text_color="#4ec9b0")

            # 显示检测结果提示
            msg_parts = []
            if detected.backend:
                msg_parts.append(f"后端: {detected.backend.command}")
            if detected.frontend:
                msg_parts.append(f"前端: {detected.frontend.command}")
            
            if msg_parts:
                messagebox.showinfo("智能检测", f"已自动检测到项目配置：\n\n" + "\n".join(msg_parts) + "\n\n如有误可手动修改")
            else:
                messagebox.showinfo("智能检测", "未检测到前后端服务，请手动配置")

        except Exception as e:
            print(f"检测失败: {e}")

    def _clear_and_insert(self, entry, value: str):
        """清空并插入值"""
        entry.delete(0, "end")
        entry.insert(0, value)

    def _suggest_port(self, service_type: str):
        """智能建议端口"""
        if service_type == "backend":
            cmd = self.backend_cmd.get().strip()
            cwd = self.backend_cwd.get().strip() or self.path_entry.get().strip()
            port_entry = self.backend_port
            hint_label = self.backend_port_hint
        else:
            cmd = self.frontend_cmd.get().strip()
            cwd = self.frontend_cwd.get().strip() or self.path_entry.get().strip()
            port_entry = self.frontend_port
            hint_label = self.frontend_port_hint
        
        if not cmd:
            messagebox.showwarning("提示", f"请先填写{service_type}服务的启动命令")
            return
        
        # 检测技术栈
        tech_stack = port_manager.detect_tech_stack(cmd, cwd)
        
        # 获取已使用的端口
        used_ports = set()
        backend_port_str = self.backend_port.get().strip()
        if backend_port_str.isdigit():
            used_ports.add(int(backend_port_str))
        frontend_port_str = self.frontend_port.get().strip()
        if frontend_port_str.isdigit():
            used_ports.add(int(frontend_port_str))
        
        # 建议端口
        try:
            project_id = self.project.id if self.is_edit else ""
            suggested_port = port_manager.suggest_port(tech_stack, project_id, used_ports)
            
            # 检查是否可用
            is_available = port_manager.is_port_available(suggested_port)
            
            # 填充端口
            port_entry.delete(0, "end")
            port_entry.insert(0, str(suggested_port))
            
            # 显示提示
            status = "✓ 可用" if is_available else "⚠ 已占用"
            hint_label.configure(
                text=f"{tech_stack.upper()} 推荐 | {status}",
                text_color="#28a745" if is_available else "#ffc107"
            )
            
            if not is_available:
                occupant = port_manager.get_port_occupant(suggested_port)
                if occupant:
                    messagebox.showwarning(
                        "端口已占用",
                        f"建议的端口 {suggested_port} 已被占用\n\n"
                        f"进程: {occupant['name']} (PID: {occupant['pid']})\n\n"
                        f"您可以继续使用此端口，但启动时可能会失败。"
                    )
        except Exception as e:
            messagebox.showerror("错误", f"端口建议失败: {e}")

    def save(self):
        """保存项目"""
        name = self.name_entry.get().strip()
        path = self.path_entry.get().strip()

        if not name:
            messagebox.showwarning("警告", "请输入项目名称")
            return
        if not path:
            messagebox.showwarning("警告", "请输入项目路径")
            return

        # 构建项目对象
        if self.is_edit:
            project = self.project
            project.name = name
            project.description = self.desc_entry.get().strip()
            project.path = path
        else:
            project = Project(
                name=name,
                description=self.desc_entry.get().strip(),
                path=path
            )

        # 后端服务
        backend_port = self.backend_port.get().strip()
        project.services["backend"] = ServiceConfig(
            enabled=self.backend_enabled.get(),
            name=self.backend_name.get().strip() or "后端服务",
            command=self.backend_cmd.get().strip(),
            cwd=self.backend_cwd.get().strip(),
            port=int(backend_port) if backend_port.isdigit() else None
        )

        # 前端服务
        frontend_port = self.frontend_port.get().strip()
        project.services["frontend"] = ServiceConfig(
            enabled=self.frontend_enabled.get(),
            name=self.frontend_name.get().strip() or "前端服务",
            cwd=self.frontend_cwd.get().strip(),
            command=self.frontend_cmd.get().strip(),
            port=int(frontend_port) if frontend_port.isdigit() else None
        )

        if self.on_save:
            self.on_save(project)

        self.destroy()


class DevManagerApp(ctk.CTk):
    """主应用窗口"""

    def __init__(self):
        super().__init__()

        self.title("DevManager - PIP端口服务管理器")
        self.geometry("1200x800")
        self.configure(fg_color=COLORS["bg_primary"])

        # 设置窗口图标
        if os.path.exists(ICON_PATH):
            self.iconbitmap(ICON_PATH)
            self.after(100, lambda: self.iconbitmap(ICON_PATH))  # 确保图标生效

        self.project_manager = enhanced_project_manager

        # 顶部栏（更现代的设计）
        header = ctk.CTkFrame(
            self,
            fg_color=COLORS["bg_secondary"],
            height=70,
            border_width=0,
            corner_radius=0
        )
        header.pack(fill="x")
        header.pack_propagate(False)

        # 左侧标题区域
        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left", padx=20, pady=15)
        
        title_label = ctk.CTkLabel(
            title_frame,
            text="⚡ DevManager",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        title_label.pack(side="left")
        
        version_label = ctk.CTkLabel(
            title_frame,
            text="Pro",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=COLORS["accent_blue"],
            fg_color=COLORS["bg_tertiary"],
            corner_radius=4,
            padx=6,
            pady=2
        )
        version_label.pack(side="left", padx=(10, 0))
        
        # 本机IPv4地址
        ipv4 = self._get_local_ipv4()
        if ipv4:
            ip_label = ctk.CTkLabel(
                title_frame,
                text=f"🌐 {ipv4}",
                font=ctk.CTkFont(size=11, family="Consolas"),
                text_color=COLORS["text_secondary"],
                fg_color=COLORS["bg_tertiary"],
                corner_radius=4,
                padx=8,
                pady=2
            )
            ip_label.pack(side="left", padx=(10, 0))

        # 端口冲突警告（更显眼的设计）
        self.conflict_warning = ctk.CTkLabel(
            header,
            text="",
            text_color="#ffffff",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=COLORS["accent_red"],
            corner_radius=6,
            padx=12,
            pady=6
        )
        self.conflict_warning.pack(side="left", padx=15)

        # 右侧按钮组
        btn_container = ctk.CTkFrame(header, fg_color="transparent")
        btn_container.pack(side="right", padx=20, pady=15)
        
        # 添加项目按钮 - 主要操作
        add_btn = ctk.CTkButton(
            btn_container,
            text="+ 添加项目",
            width=130,
            height=42,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS["cta_blue"],
            hover_color=COLORS["accent_blue"],
            corner_radius=10,
            command=self.add_project
        )
        add_btn.pack(side="right", padx=(10, 0))

        # 端口管理按钮
        port_manager_btn = ctk.CTkButton(
            btn_container,
            text="端口管理",
            width=110,
            height=42,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_primary"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=10,
            command=self.open_port_manager
        )
        port_manager_btn.pack(side="right", padx=(10, 0))
        
        # 刷新按钮
        refresh_btn = ctk.CTkButton(
            btn_container,
            text="🔄",
            width=42,
            height=42,
            font=ctk.CTkFont(size=16),
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["bg_hover"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=10,
            command=self.refresh_projects
        )
        refresh_btn.pack(side="right")

        # 项目列表容器（带分隔线）
        separator = ctk.CTkFrame(self, fg_color=COLORS["border"], height=1)
        separator.pack(fill="x")
        
        self.scroll_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            corner_radius=0
        )
        self.scroll_frame.pack(fill="both", expand=True, padx=32, pady=32)

        # 加载项目
        self.refresh_projects()
        
        # 检查端口冲突
        self.check_port_conflicts()

        # 窗口关闭时停止所有服务
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def refresh_projects(self):
        """刷新项目列表"""
        # 清空现有内容
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        projects = self.project_manager.get_all()

        if not projects:
            # 空状态设计
            empty_frame = ctk.CTkFrame(
                self.scroll_frame,
                fg_color=COLORS["bg_tertiary"],
                corner_radius=12,
                border_width=2,
                border_color=COLORS["border"]
            )
            empty_frame.pack(pady=100, padx=50)
            
            empty_icon = ctk.CTkLabel(
                empty_frame,
                text="📦",
                font=ctk.CTkFont(size=48)
            )
            empty_icon.pack(pady=(40, 10))
            
            empty_label = ctk.CTkLabel(
                empty_frame,
                text="暂无项目",
                text_color=COLORS["text_primary"],
                font=ctk.CTkFont(size=18, weight="bold")
            )
            empty_label.pack(pady=(0, 5))
            
            empty_hint = ctk.CTkLabel(
                empty_frame,
                text="点击右上角「+ 添加项目」开始管理你的开发项目",
                text_color=COLORS["text_secondary"],
                font=ctk.CTkFont(size=12)
            )
            empty_hint.pack(pady=(0, 40))
            return

        for project in projects:
            card = ProjectCard(
                self.scroll_frame,
                project,
                on_edit=self.edit_project,
                on_delete=self.delete_project
            )
            card.pack(fill="x", pady=(0, 20))
        
        # 刷新后检查冲突
        self.check_port_conflicts()

    def add_project(self):
        """添加项目"""
        EnhancedProjectFormDialog(self, on_save=self.refresh_projects)

    def edit_project(self, project: Project):
        """编辑项目"""
        EnhancedProjectFormDialog(self, project=project, on_save=self.refresh_projects)

    def _save_project(self, project: Project):
        """保存项目（已废弃，新版本直接在对话框中保存）"""
        pass

    def delete_project(self, project: Project):
        """删除项目"""
        if messagebox.askyesno("确认删除", f"确定要删除项目「{project.name}」吗？"):
            # 先停止该项目的所有服务
            for service_key in project.services:
                process_manager.stop_service(project.id, service_key)
            self.project_manager.delete(project.id)
            self.refresh_projects()

    
    def open_port_manager(self):
        """打开端口管理器"""
        PortManagerDialog(self, self.project_manager.get_all())
    
    def check_port_conflicts(self):
        """检查端口冲突并显示警告"""
        conflicts = port_manager.check_conflicts(self.project_manager.get_all())
        if conflicts:
            conflict_count = len(conflicts)
            self.conflict_warning.configure(text=f"⚠️ {conflict_count} 个端口冲突")
            self.conflict_warning.pack(side="left", padx=15)
        else:
            self.conflict_warning.pack_forget()

    def _get_local_ipv4(self) -> str:
        """获取本机IPv4地址（局域网IP）- 从以太网或WiFi适配器获取"""
        try:
            import subprocess
            import re
            
            # 执行 ipconfig 命令
            result = subprocess.run(
                ["ipconfig"],
                capture_output=True,
                text=True,
                encoding='gbk',  # Windows中文系统使用gbk编码
                timeout=5
            )
            
            if result.returncode != 0:
                return None
            
            output = result.stdout
            
            # 查找以太网或WiFi适配器的IPv4地址
            # 匹配模式：先找到适配器名称，然后找到对应的IPv4地址
            lines = output.split('\n')
            current_adapter = None
            
            for i, line in enumerate(lines):
                # 检测适配器名称（以太网、WLAN、Wi-Fi等）
                if '适配器' in line or 'adapter' in line.lower():
                    adapter_name = line.strip()
                    # 优先使用以太网或WiFi，跳过虚拟适配器
                    if any(keyword in adapter_name for keyword in ['以太网', 'Ethernet', 'WLAN', 'Wi-Fi', '无线']):
                        if not any(skip in adapter_name for skip in ['虚拟', 'Virtual', 'VPN', 'VMware', 'VirtualBox', 'Hyper-V']):
                            current_adapter = adapter_name
                
                # 在当前适配器下查找IPv4地址
                if current_adapter and 'IPv4' in line:
                    # 提取IP地址（格式：IPv4 地址 . . . . . . . . . . . . : 10.250.9.82）
                    match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', line)
                    if match:
                        ip = match.group(1)
                        # 排除本地回环地址和APIPA地址
                        if not ip.startswith('127.') and not ip.startswith('169.254.'):
                            return ip
            
            return None
        except:
            return None
    
    def on_close(self):
        """关闭应用"""
        if messagebox.askyesno("退出", "退出将停止所有运行中的服务，确定退出吗？"):
            process_manager.stop_all()
            self.destroy()


class ProcessScanDialog(ctk.CTkToplevel):
    """进程扫描对话框"""

    def __init__(self, master, projects: List[Project]):
        super().__init__(master)
        self.projects = projects
        self.external_processes: List[ExternalProcess] = []

        self.title("扫描系统进程")
        self.geometry("900x600")
        self.configure(fg_color="#1a1a1a")

        self.transient(master)
        self.grab_set()

        # 顶部说明
        info_frame = ctk.CTkFrame(self, fg_color="#2b2b2b", corner_radius=8)
        info_frame.pack(fill="x", padx=20, pady=(20, 10))

        ctk.CTkLabel(
            info_frame,
            text="🔍 扫描系统中运行的开发相关进程",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=15, pady=(10, 5))

        ctk.CTkLabel(
            info_frame,
            text="检测 cmd、PowerShell、Python、Node.js 等进程，并根据工作目录匹配到已配置的项目",
            text_color="#888888",
            font=ctk.CTkFont(size=12)
        ).pack(anchor="w", padx=15, pady=(0, 10))

        # 扫描按钮
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=10)

        self.scan_btn = ctk.CTkButton(
            btn_frame,
            text="开始扫描",
            width=120,
            height=35,
            fg_color="#17a2b8",
            hover_color="#138496",
            command=self.do_scan
        )
        self.scan_btn.pack(side="left")

        self.status_label = ctk.CTkLabel(
            btn_frame,
            text="",
            text_color="#888888"
        )
        self.status_label.pack(side="left", padx=15)

        # 结果列表
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # 底部按钮
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.pack(fill="x", padx=20, pady=(0, 20))

        ctk.CTkButton(
            bottom_frame,
            text="关闭",
            width=100,
            fg_color="#6c757d",
            hover_color="#5a6268",
            command=self.destroy
        ).pack(side="right")

        # 自动开始扫描
        self.after(100, self.do_scan)

    def do_scan(self):
        """执行扫描"""
        self.scan_btn.configure(state="disabled")
        self.status_label.configure(text="正在扫描...")

        # 清空结果
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        # 在后台线程执行扫描
        def scan_thread():
            processes = scan_and_match(self.projects)
            self.after(0, lambda: self.show_results(processes))

        threading.Thread(target=scan_thread, daemon=True).start()

    def show_results(self, processes: List[ExternalProcess]):
        """显示扫描结果"""
        self.scan_btn.configure(state="normal")
        self.external_processes = processes

        if not processes:
            self.status_label.configure(text="未发现相关进程")
            ctk.CTkLabel(
                self.scroll_frame,
                text="未检测到运行中的开发相关进程",
                text_color="#666666",
                font=ctk.CTkFont(size=14)
            ).pack(pady=30)
            return

        self.status_label.configure(text=f"发现 {len(processes)} 个进程")

        # 按匹配状态分组显示
        matched = [p for p in processes if p.matched_project_id]
        unmatched = [p for p in processes if not p.matched_project_id]

        if matched:
            self._create_section("✅ 已匹配到项目的进程")
            for proc in matched:
                self._create_process_card(proc, matched=True)

        if unmatched:
            self._create_section("❓ 未匹配的进程")
            for proc in unmatched:
                self._create_process_card(proc, matched=False)

    def _create_section(self, title: str):
        """创建分区标题"""
        label = ctk.CTkLabel(
            self.scroll_frame,
            text=title,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        label.pack(anchor="w", pady=(15, 8))

    def _create_process_card(self, proc: ExternalProcess, matched: bool):
        """创建进程卡片"""
        card = ctk.CTkFrame(self.scroll_frame, fg_color="#2b2b2b", corner_radius=8)
        card.pack(fill="x", pady=(0, 8))

        # 头部：进程名和 PID
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(10, 5))

        name_text = f"{proc.name}"
        if matched:
            # 找到匹配的项目名
            project_name = "未知项目"
            for p in self.projects:
                if p.id == proc.matched_project_id:
                    project_name = p.name
                    break
            name_text += f"  →  {project_name}"
            if proc.matched_service:
                service_text = {"frontend": "前端", "backend": "后端"}.get(proc.matched_service, proc.matched_service)
                name_text += f" ({service_text})"

        ctk.CTkLabel(
            header,
            text=name_text,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#28a745" if matched else "#ffc107"
        ).pack(side="left")

        ctk.CTkLabel(
            header,
            text=f"PID: {proc.pid}",
            text_color="#888888",
            font=ctk.CTkFont(size=11)
        ).pack(side="right")

        # 工作目录
        if proc.cwd:
            ctk.CTkLabel(
                card,
                text=f"📁 {proc.cwd}",
                text_color="#666666",
                font=ctk.CTkFont(size=11)
            ).pack(anchor="w", padx=12)

        # 命令行（截断显示）
        if proc.command_line:
            cmd_display = proc.command_line[:100] + "..." if len(proc.command_line) > 100 else proc.command_line
            ctk.CTkLabel(
                card,
                text=f"💻 {cmd_display}",
                text_color="#666666",
                font=ctk.CTkFont(size=11)
            ).pack(anchor="w", padx=12, pady=(0, 10))


def main():
    app = DevManagerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
