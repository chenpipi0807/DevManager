"""DevManager - 本地开发项目管理面板 (GUI版)"""
import customtkinter as ctk
from tkinter import messagebox, filedialog
import threading
import os
from typing import Optional, Dict, List
from models import Project, ServiceConfig, ProjectManager
from process_manager import process_manager
from process_scanner import scan_and_match, ExternalProcess
from project_detector import detect_project

# 图标路径
ICON_PATH = os.path.join(os.path.dirname(__file__), "icon.ico")

# Windows 任务栏图标设置（必须在创建窗口前调用）
try:
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("DevManager.App")
except:
    pass

# 设置主题
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class ServiceFrame(ctk.CTkFrame):
    """单个服务控制组件"""

    def __init__(self, master, project: Project, service_key: str, service: ServiceConfig, **kwargs):
        super().__init__(master, **kwargs)
        self.project = project
        self.service_key = service_key
        self.service = service

        self.configure(fg_color="#2b2b2b", corner_radius=6)

        # 单行布局：名称 | 命令 | 端口 | 状态 | 按钮
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="x", padx=8, pady=6)

        # 左侧：服务名称
        self.name_label = ctk.CTkLabel(
            content,
            text=service.name or service_key,
            font=ctk.CTkFont(size=12, weight="bold"),
            width=120,
            anchor="w"
        )
        self.name_label.pack(side="left")

        # 命令（简短显示）
        cmd_short = service.command[:30] + "..." if len(service.command) > 30 else service.command
        cmd_label = ctk.CTkLabel(
            content,
            text=cmd_short,
            text_color="#888888",
            font=ctk.CTkFont(size=10),
            width=180,
            anchor="w"
        )
        cmd_label.pack(side="left", padx=(5, 0))

        # 端口
        if service.port:
            port_label = ctk.CTkLabel(
                content,
                text=f":{service.port}",
                text_color="#666666",
                font=ctk.CTkFont(size=10),
                width=50
            )
            port_label.pack(side="left")

        # 右侧按钮组
        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.pack(side="right")

        # 状态标签
        self.status_label = ctk.CTkLabel(
            btn_frame,
            text="● 停止",
            text_color="#888888",
            font=ctk.CTkFont(size=10),
            width=50
        )
        self.status_label.pack(side="left", padx=(0, 8))

        self.start_btn = ctk.CTkButton(
            btn_frame,
            text="启动",
            width=50,
            height=24,
            font=ctk.CTkFont(size=11),
            fg_color="#28a745",
            hover_color="#218838",
            command=self.start_service
        )
        self.start_btn.pack(side="left", padx=(0, 4))

        self.stop_btn = ctk.CTkButton(
            btn_frame,
            text="停止",
            width=50,
            height=24,
            font=ctk.CTkFont(size=11),
            fg_color="#dc3545",
            hover_color="#c82333",
            command=self.stop_service
        )
        self.stop_btn.pack(side="left", padx=(0, 4))

        self.log_btn = ctk.CTkButton(
            btn_frame,
            text="日志",
            width=50,
            height=24,
            font=ctk.CTkFont(size=11),
            fg_color="#6c757d",
            hover_color="#5a6268",
            command=self.show_logs
        )
        self.log_btn.pack(side="left")

        self.update_status()

    def start_service(self):
        """启动服务"""
        if not self.service.command:
            messagebox.showwarning("警告", "未配置启动命令")
            return

        cwd = self.service.cwd or self.project.path
        success = process_manager.start_service(
            self.project.id,
            self.service_key,
            self.service.command,
            cwd,
            self.service.env
        )
        if success:
            self.after(500, self.update_status)

    def stop_service(self):
        """停止服务"""
        process_manager.stop_service(self.project.id, self.service_key)
        self.after(500, self.update_status)

    def show_logs(self):
        """显示日志窗口"""
        LogWindow(self, self.project, self.service_key, self.service.name or self.service_key)

    def update_status(self):
        """更新状态显示"""
        running = process_manager.is_running(self.project.id, self.service_key)
        if running:
            self.status_label.configure(text="● 运行", text_color="#28a745")
            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
        else:
            self.status_label.configure(text="● 停止", text_color="#888888")
            self.start_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")


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
        process_manager.add_log_callback(project.id, service_key, self.log_callback)

        # 窗口关闭时移除回调
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def load_logs(self):
        """加载历史日志"""
        logs = process_manager.get_logs(self.project.id, self.service_key)
        for line in logs:
            self.log_text.insert("end", line + "\n")
        self.log_text.see("end")

    def on_new_log(self, line: str):
        """收到新日志"""
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

        self.configure(fg_color="#1e1e1e", corner_radius=10)

        # 项目头部
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=(15, 10))

        name_label = ctk.CTkLabel(
            header,
            text=project.name,
            font=ctk.CTkFont(size=18, weight="bold")
        )
        name_label.pack(side="left")

        # 操作按钮
        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.pack(side="right")

        ctk.CTkButton(
            btn_frame,
            text="编辑",
            width=60,
            height=26,
            fg_color="#0d6efd",
            hover_color="#0b5ed7",
            command=lambda: on_edit(project)
        ).pack(side="left", padx=(0, 5))

        ctk.CTkButton(
            btn_frame,
            text="删除",
            width=60,
            height=26,
            fg_color="#dc3545",
            hover_color="#c82333",
            command=lambda: on_delete(project)
        ).pack(side="left")

        # 项目描述
        if project.description:
            desc_label = ctk.CTkLabel(
                self,
                text=project.description,
                text_color="#888888",
                font=ctk.CTkFont(size=12)
            )
            desc_label.pack(anchor="w", padx=15)

        # 项目路径
        path_label = ctk.CTkLabel(
            self,
            text=f"📁 {project.path}",
            text_color="#666666",
            font=ctk.CTkFont(size=11)
        )
        path_label.pack(anchor="w", padx=15, pady=(5, 10))

        # 服务列表
        services_frame = ctk.CTkFrame(self, fg_color="transparent")
        services_frame.pack(fill="x", padx=15, pady=(0, 15))

        for key, service in project.services.items():
            if service.enabled:
                service_frame = ServiceFrame(services_frame, project, key, service)
                service_frame.pack(fill="x", pady=(0, 8))


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
        self.backend_cmd = ctk.CTkEntry(self.scroll_frame, width=400, placeholder_text="python main.py")
        self.backend_cmd.pack(anchor="w")

        ctk.CTkLabel(self.scroll_frame, text="工作目录 (留空则使用项目路径)").pack(anchor="w", pady=(5, 2))
        self.backend_cwd = ctk.CTkEntry(self.scroll_frame, width=400)
        self.backend_cwd.pack(anchor="w")

        ctk.CTkLabel(self.scroll_frame, text="端口").pack(anchor="w", pady=(5, 2))
        self.backend_port = ctk.CTkEntry(self.scroll_frame, width=100, placeholder_text="8000")
        self.backend_port.pack(anchor="w")

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

        ctk.CTkLabel(self.scroll_frame, text="端口").pack(anchor="w", pady=(5, 2))
        self.frontend_port = ctk.CTkEntry(self.scroll_frame, width=100, placeholder_text="5173")
        self.frontend_port.pack(anchor="w")

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
            
            # 填充前端服务
            if detected.frontend:
                self.frontend_enabled.select()
                self._clear_and_insert(self.frontend_name, detected.frontend.name)
                self._clear_and_insert(self.frontend_cmd, detected.frontend.command)
                self._clear_and_insert(self.frontend_cwd, detected.frontend.cwd)
                if detected.frontend.port:
                    self._clear_and_insert(self.frontend_port, str(detected.frontend.port))

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
            name=self.frontend_name.get().strip() or "后端服务",
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

        self.title("DevManager - 本地开发项目管理")
        self.geometry("900x700")
        self.configure(fg_color="#121212")

        # 设置窗口图标
        if os.path.exists(ICON_PATH):
            self.iconbitmap(ICON_PATH)
            self.after(100, lambda: self.iconbitmap(ICON_PATH))  # 确保图标生效

        self.project_manager = ProjectManager()

        # 顶部栏
        header = ctk.CTkFrame(self, fg_color="#1e1e1e", height=60)
        header.pack(fill="x")
        header.pack_propagate(False)

        title_label = ctk.CTkLabel(
            header,
            text="🚀 DevManager",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        title_label.pack(side="left", padx=20, pady=15)

        add_btn = ctk.CTkButton(
            header,
            text="+ 添加项目",
            width=120,
            height=35,
            fg_color="#0d6efd",
            hover_color="#0b5ed7",
            command=self.add_project
        )
        add_btn.pack(side="right", padx=20, pady=12)

        refresh_btn = ctk.CTkButton(
            header,
            text="刷新",
            width=80,
            height=35,
            fg_color="#6c757d",
            hover_color="#5a6268",
            command=self.refresh_projects
        )
        refresh_btn.pack(side="right", pady=12)

        scan_btn = ctk.CTkButton(
            header,
            text="扫描进程",
            width=100,
            height=35,
            fg_color="#17a2b8",
            hover_color="#138496",
            command=self.scan_processes
        )
        scan_btn.pack(side="right", padx=(0, 10), pady=12)

        # 项目列表容器
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # 加载项目
        self.refresh_projects()

        # 窗口关闭时停止所有服务
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def refresh_projects(self):
        """刷新项目列表"""
        # 清空现有内容
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        projects = self.project_manager.get_all()

        if not projects:
            empty_label = ctk.CTkLabel(
                self.scroll_frame,
                text="暂无项目，点击「添加项目」开始",
                text_color="#666666",
                font=ctk.CTkFont(size=14)
            )
            empty_label.pack(pady=50)
            return

        for project in projects:
            card = ProjectCard(
                self.scroll_frame,
                project,
                on_edit=self.edit_project,
                on_delete=self.delete_project
            )
            card.pack(fill="x", pady=(0, 15))

    def add_project(self):
        """添加项目"""
        ProjectFormDialog(self, on_save=self._save_project)

    def edit_project(self, project: Project):
        """编辑项目"""
        ProjectFormDialog(self, project=project, on_save=self._save_project)

    def _save_project(self, project: Project):
        """保存项目"""
        if project.id in self.project_manager.projects:
            self.project_manager.update(project)
        else:
            self.project_manager.add(project)
        self.refresh_projects()

    def delete_project(self, project: Project):
        """删除项目"""
        if messagebox.askyesno("确认删除", f"确定要删除项目「{project.name}」吗？"):
            # 先停止该项目的所有服务
            for service_key in project.services:
                process_manager.stop_service(project.id, service_key)
            self.project_manager.delete(project.id)
            self.refresh_projects()

    def scan_processes(self):
        """扫描系统进程"""
        ProcessScanDialog(self, self.project_manager.get_all())

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
