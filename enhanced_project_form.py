"""增强的项目表单对话框 - 支持企业级配置"""
import os
import customtkinter as ctk
from tkinter import filedialog, messagebox
from typing import Optional
from enhanced_models import (
    Project, ServiceConfig, PortConfig, PythonEnvironment,
    ProjectMetadata, enhanced_project_manager
)
from enhanced_project_detector import enhanced_detector


class EnhancedProjectFormDialog(ctk.CTkToplevel):
    """增强的项目表单对话框"""
    
    def __init__(self, master, project: Optional[Project] = None, on_save=None):
        super().__init__(master)
        self.project = project
        self.on_save = on_save
        self.is_edit = project is not None
        
        self.title("编辑项目" if self.is_edit else "添加项目")
        self.geometry("800x900")
        self.configure(fg_color="#FAFAFA")
        
        # 使窗口模态
        self.transient(master)
        self.grab_set()
        
        # 检测结果
        self.detected_services = {}
        
        # 创建UI
        self._create_ui()
        
        # 填充数据
        if self.is_edit:
            self._fill_data()
    
    def _create_ui(self):
        """创建UI"""
        # 滚动容器
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 基本信息
        self._create_basic_info_section()
        
        # 自动检测按钮
        self._create_auto_detect_section()
        
        # 后端服务
        self._create_backend_section()
        
        # 前端服务
        self._create_frontend_section()
        
        # 项目元数据
        self._create_metadata_section()
        
        # 底部按钮
        self._create_buttons()
    
    def _create_section_title(self, title: str):
        """创建分区标题"""
        label = ctk.CTkLabel(
            self.scroll_frame,
            text=title,
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#000000"
        )
        label.pack(anchor="w", pady=(20, 5))
        separator = ctk.CTkFrame(self.scroll_frame, height=2, fg_color="#E5E5E5")
        separator.pack(fill="x", pady=(0, 10))
    
    def _create_basic_info_section(self):
        """创建基本信息区域"""
        self._create_section_title("📋 基本信息")
        
        ctk.CTkLabel(self.scroll_frame, text="项目名称 *", text_color="#cccccc").pack(anchor="w", pady=(5, 2))
        self.name_entry = ctk.CTkEntry(self.scroll_frame, width=500, height=35)
        self.name_entry.pack(anchor="w")
        
        ctk.CTkLabel(self.scroll_frame, text="项目描述", text_color="#cccccc").pack(anchor="w", pady=(10, 2))
        self.desc_entry = ctk.CTkEntry(self.scroll_frame, width=500, height=35)
        self.desc_entry.pack(anchor="w")
        
        ctk.CTkLabel(self.scroll_frame, text="项目路径 *", text_color="#cccccc").pack(anchor="w", pady=(10, 2))
        path_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        path_frame.pack(anchor="w")
        self.path_entry = ctk.CTkEntry(path_frame, width=420, height=35)
        self.path_entry.pack(side="left")
        ctk.CTkButton(
            path_frame,
            text="📁 浏览",
            width=70,
            height=35,
            command=self._browse_path
        ).pack(side="left", padx=(5, 0))
    
    def _create_auto_detect_section(self):
        """创建自动检测区域"""
        detect_frame = ctk.CTkFrame(self.scroll_frame, fg_color="#FFFFFF", corner_radius=8, border_width=1, border_color="#E5E5E5")
        detect_frame.pack(fill="x", pady=(15, 0))
        
        ctk.CTkLabel(
            detect_frame,
            text="💡 智能检测",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#000000"
        ).pack(anchor="w", padx=15, pady=(15, 5))
        
        ctk.CTkLabel(
            detect_frame,
            text="自动扫描项目目录，识别前后端结构、技术栈、端口配置和Python环境",
            text_color="#8E8E93",
            font=ctk.CTkFont(size=11)
        ).pack(anchor="w", padx=15, pady=(0, 10))
        
        ctk.CTkButton(
            detect_frame,
            text="🔍 开始自动检测",
            width=150,
            height=35,
            fg_color="#000000",
            hover_color="#333333",
            text_color="#FFFFFF",
            command=self._auto_detect
        ).pack(anchor="w", padx=15, pady=(0, 15))
    
    def _create_backend_section(self):
        """创建后端服务配置区域"""
        self._create_section_title("🔧 后端服务")
        
        self.backend_enabled = ctk.CTkCheckBox(
            self.scroll_frame,
            text="启用后端服务",
            font=ctk.CTkFont(size=13)
        )
        self.backend_enabled.pack(anchor="w", pady=(5, 10))
        
        # 服务名称
        ctk.CTkLabel(self.scroll_frame, text="服务名称", text_color="#cccccc").pack(anchor="w", pady=(5, 2))
        self.backend_name = ctk.CTkEntry(self.scroll_frame, width=500, height=35, placeholder_text="后端服务")
        self.backend_name.pack(anchor="w")
        
        # 技术栈
        ctk.CTkLabel(self.scroll_frame, text="技术栈", text_color="#cccccc").pack(anchor="w", pady=(10, 2))
        self.backend_tech = ctk.CTkEntry(self.scroll_frame, width=500, height=35, placeholder_text="fastapi / flask / django")
        self.backend_tech.pack(anchor="w")
        
        # 工作目录
        ctk.CTkLabel(self.scroll_frame, text="工作目录", text_color="#cccccc").pack(anchor="w", pady=(10, 2))
        self.backend_cwd = ctk.CTkEntry(self.scroll_frame, width=500, height=35, placeholder_text="留空则使用项目根路径")
        self.backend_cwd.pack(anchor="w")
        
        # 启动文件
        ctk.CTkLabel(self.scroll_frame, text="启动文件", text_color="#cccccc").pack(anchor="w", pady=(10, 2))
        self.backend_startup = ctk.CTkEntry(self.scroll_frame, width=500, height=35, placeholder_text="main.py / app.py")
        self.backend_startup.pack(anchor="w")
        
        # 启动命令
        ctk.CTkLabel(self.scroll_frame, text="启动命令", text_color="#cccccc").pack(anchor="w", pady=(10, 2))
        self.backend_cmd = ctk.CTkEntry(self.scroll_frame, width=500, height=35)
        self.backend_cmd.pack(anchor="w")
        
        # 命令模板
        ctk.CTkLabel(self.scroll_frame, text="命令模板 (支持变量)", text_color="#cccccc").pack(anchor="w", pady=(10, 2))
        self.backend_cmd_template = ctk.CTkEntry(
            self.scroll_frame,
            width=500,
            height=35,
            placeholder_text="{python_env} -m uvicorn main:app --reload --port {port}"
        )
        self.backend_cmd_template.pack(anchor="w")
        
        # 端口配置
        port_frame = ctk.CTkFrame(self.scroll_frame, fg_color="#F5F5F5", corner_radius=6)
        port_frame.pack(fill="x", pady=(10, 0))
        
        ctk.CTkLabel(
            port_frame,
            text="端口配置",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        port_row = ctk.CTkFrame(port_frame, fg_color="transparent")
        port_row.pack(fill="x", padx=10, pady=(0, 5))
        
        ctk.CTkLabel(port_row, text="端口:", text_color="#8E8E93").pack(side="left", padx=(10, 0))
        self.backend_port = ctk.CTkEntry(port_row, width=100, height=30, placeholder_text="8000")
        self.backend_port.pack(side="left", padx=5)
        
        ctk.CTkLabel(
            port_row,
            text="(启动命令会使用此端口)",
            text_color="#8E8E93",
            font=ctk.CTkFont(size=10)
        ).pack(side="left", padx=(10, 0))
        
        self.backend_port_source = ctk.CTkLabel(
            port_frame,
            text="",
            text_color="#8E8E93",
            font=ctk.CTkFont(size=10)
        )
        self.backend_port_source.pack(anchor="w", padx=10, pady=(0, 10))
        
        # Python环境
        ctk.CTkLabel(self.scroll_frame, text="Python环境", text_color="#cccccc").pack(anchor="w", pady=(10, 2))
        
        python_envs = enhanced_detector.get_python_environments()
        env_options = ["不指定"] + [f"{env.name} ({env.version})" for env in python_envs]
        self.backend_python_var = ctk.StringVar(value=env_options[0] if env_options else "不指定")
        self.backend_python_menu = ctk.CTkOptionMenu(
            self.scroll_frame,
            values=env_options,
            variable=self.backend_python_var,
            width=500,
            height=35
        )
        self.backend_python_menu.pack(anchor="w")
        self.python_envs_list = python_envs
        
        # 测试启动按钮
        ctk.CTkButton(
            self.scroll_frame,
            text="🧪 测试启动 (快速验证Python环境和依赖)",
            width=500,
            height=35,
            fg_color="#000000",
            hover_color="#333333",
            text_color="#FFFFFF",
            font=ctk.CTkFont(size=12),
            command=self._test_backend_startup
        ).pack(anchor="w", pady=(10, 0))
    
    def _create_frontend_section(self):
        """创建前端服务配置区域"""
        self._create_section_title("🎨 前端服务")
        
        self.frontend_enabled = ctk.CTkCheckBox(
            self.scroll_frame,
            text="启用前端服务",
            font=ctk.CTkFont(size=13)
        )
        self.frontend_enabled.pack(anchor="w", pady=(5, 10))
        
        # 服务名称
        ctk.CTkLabel(self.scroll_frame, text="服务名称", text_color="#cccccc").pack(anchor="w", pady=(5, 2))
        self.frontend_name = ctk.CTkEntry(self.scroll_frame, width=500, height=35, placeholder_text="前端服务")
        self.frontend_name.pack(anchor="w")
        
        # 技术栈
        ctk.CTkLabel(self.scroll_frame, text="技术栈", text_color="#cccccc").pack(anchor="w", pady=(10, 2))
        self.frontend_tech = ctk.CTkEntry(self.scroll_frame, width=500, height=35, placeholder_text="vite / react / vue")
        self.frontend_tech.pack(anchor="w")
        
        # 工作目录
        ctk.CTkLabel(self.scroll_frame, text="工作目录", text_color="#cccccc").pack(anchor="w", pady=(10, 2))
        self.frontend_cwd = ctk.CTkEntry(self.scroll_frame, width=500, height=35, placeholder_text="留空则使用项目根路径")
        self.frontend_cwd.pack(anchor="w")
        
        # 启动文件
        ctk.CTkLabel(self.scroll_frame, text="启动文件", text_color="#cccccc").pack(anchor="w", pady=(10, 2))
        self.frontend_startup = ctk.CTkEntry(self.scroll_frame, width=500, height=35, placeholder_text="package.json")
        self.frontend_startup.pack(anchor="w")
        
        # 启动命令
        ctk.CTkLabel(self.scroll_frame, text="启动命令", text_color="#cccccc").pack(anchor="w", pady=(10, 2))
        self.frontend_cmd = ctk.CTkEntry(self.scroll_frame, width=500, height=35, placeholder_text="npm run dev")
        self.frontend_cmd.pack(anchor="w")
        
        # 命令模板
        ctk.CTkLabel(self.scroll_frame, text="命令模板 (支持变量)", text_color="#cccccc").pack(anchor="w", pady=(10, 2))
        self.frontend_cmd_template = ctk.CTkEntry(
            self.scroll_frame,
            width=500,
            height=35,
            placeholder_text="npm run dev -- --port {port}"
        )
        self.frontend_cmd_template.pack(anchor="w")
        
        # 端口配置
        port_frame = ctk.CTkFrame(self.scroll_frame, fg_color="#F5F5F5", corner_radius=6)
        port_frame.pack(fill="x", pady=(10, 0))
        
        ctk.CTkLabel(
            port_frame,
            text="端口配置",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        port_row = ctk.CTkFrame(port_frame, fg_color="transparent")
        port_row.pack(fill="x", padx=10, pady=(0, 5))
        
        ctk.CTkLabel(port_row, text="端口:", text_color="#8E8E93").pack(side="left", padx=(10, 0))
        self.frontend_port = ctk.CTkEntry(port_row, width=100, height=30, placeholder_text="5173")
        self.frontend_port.pack(side="left", padx=5)
        
        ctk.CTkLabel(
            port_row,
            text="(启动命令会使用此端口)",
            text_color="#8E8E93",
            font=ctk.CTkFont(size=10)
        ).pack(side="left", padx=(10, 0))
        
        self.frontend_port_source = ctk.CTkLabel(
            port_frame,
            text="",
            text_color="#8E8E93",
            font=ctk.CTkFont(size=10)
        )
        self.frontend_port_source.pack(anchor="w", padx=10, pady=(0, 10))
        
        # 测试启动按钮
        ctk.CTkButton(
            self.scroll_frame,
            text="🧪 测试启动 (快速验证前端环境和依赖)",
            width=500,
            height=35,
            fg_color="#000000",
            hover_color="#333333",
            text_color="#FFFFFF",
            font=ctk.CTkFont(size=12),
            command=self._test_frontend_startup
        ).pack(anchor="w", pady=(10, 0))
    
    def _create_metadata_section(self):
        """创建项目元数据区域"""
        self._create_section_title("📊 项目元数据")
        
        # 标签
        ctk.CTkLabel(self.scroll_frame, text="标签 (逗号分隔)", text_color="#cccccc").pack(anchor="w", pady=(5, 2))
        self.tags_entry = ctk.CTkEntry(self.scroll_frame, width=500, height=35, placeholder_text="重要, 生产环境")
        self.tags_entry.pack(anchor="w")
        
        # 分类和优先级
        row = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        row.pack(fill="x", pady=(10, 0))
        
        left_col = ctk.CTkFrame(row, fg_color="transparent")
        left_col.pack(side="left", fill="x", expand=True)
        
        ctk.CTkLabel(left_col, text="分类", text_color="#cccccc").pack(anchor="w", pady=(0, 2))
        self.category_entry = ctk.CTkEntry(left_col, width=240, height=35, placeholder_text="Web应用")
        self.category_entry.pack(anchor="w")
        
        right_col = ctk.CTkFrame(row, fg_color="transparent")
        right_col.pack(side="left", fill="x", expand=True, padx=(20, 0))
        
        ctk.CTkLabel(right_col, text="优先级", text_color="#cccccc").pack(anchor="w", pady=(0, 2))
        self.priority_var = ctk.StringVar(value="normal")
        self.priority_menu = ctk.CTkOptionMenu(
            right_col,
            values=["low", "normal", "high"],
            variable=self.priority_var,
            width=240,
            height=35
        )
        self.priority_menu.pack(anchor="w")
        
        # 备注
        ctk.CTkLabel(self.scroll_frame, text="备注", text_color="#cccccc").pack(anchor="w", pady=(10, 2))
        self.notes_text = ctk.CTkTextbox(self.scroll_frame, width=500, height=80)
        self.notes_text.pack(anchor="w")
    
    def _create_buttons(self):
        """创建底部按钮"""
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkButton(
            btn_frame,
            text="取消",
            width=120,
            height=40,
            fg_color="#FFFFFF",
            hover_color="#F5F5F5",
            text_color="#000000",
            border_width=1,
            border_color="#E5E5E5",
            command=self.destroy
        ).pack(side="right")
        
        ctk.CTkButton(
            btn_frame,
            text="💾 保存项目",
            width=120,
            height=40,
            fg_color="#000000",
            hover_color="#333333",
            text_color="#FFFFFF",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._save
        ).pack(side="right", padx=(0, 10))
    
    def _browse_path(self):
        """浏览项目路径"""
        path = filedialog.askdirectory(title="选择项目目录")
        if path:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, path)
    
    def _auto_detect(self):
        """自动检测项目"""
        project_path = self.path_entry.get().strip()
        if not project_path:
            messagebox.showwarning("提示", "请先选择项目路径")
            return
        
        if not os.path.exists(project_path):
            messagebox.showerror("错误", "项目路径不存在")
            return
        
        # 显示检测中
        progress = ctk.CTkToplevel(self)
        progress.title("检测中")
        progress.geometry("300x100")
        progress.transient(self)
        progress.grab_set()
        
        ctk.CTkLabel(
            progress,
            text="🔍 正在扫描项目...",
            font=ctk.CTkFont(size=14)
        ).pack(pady=30)
        
        progress.update()
        
        # 执行检测
        try:
            self.detected_services = enhanced_detector.detect_project(project_path)
            
            # 填充检测结果
            if 'backend' in self.detected_services:
                self._fill_backend_detection(self.detected_services['backend'])
            
            if 'frontend' in self.detected_services:
                self._fill_frontend_detection(self.detected_services['frontend'])
            
            progress.destroy()
            messagebox.showinfo("成功", f"检测完成！\n找到 {len(self.detected_services)} 个服务")
        except Exception as e:
            progress.destroy()
            messagebox.showerror("错误", f"检测失败: {e}")
    
    def _fill_backend_detection(self, service):
        """填充后端检测结果"""
        self.backend_enabled.select()
        self.backend_name.delete(0, "end")
        self.backend_name.insert(0, service.name)
        
        self.backend_tech.delete(0, "end")
        self.backend_tech.insert(0, service.tech_stack)
        
        self.backend_cwd.delete(0, "end")
        self.backend_cwd.insert(0, service.working_dir)
        
        self.backend_startup.delete(0, "end")
        self.backend_startup.insert(0, service.startup_file)
        
        self.backend_cmd.delete(0, "end")
        self.backend_cmd.insert(0, service.command)
        
        self.backend_cmd_template.delete(0, "end")
        self.backend_cmd_template.insert(0, service.command_template)
        
        if service.port_config:
            self.backend_port.delete(0, "end")
            self.backend_port.insert(0, str(service.port_config.port))
            
            source_text = f"来源: {service.port_config.port_source} (置信度: {service.port_config.confidence:.0%})"
            self.backend_port_source.configure(text=source_text)
        
        if service.python_env:
            # 选择对应的Python环境
            for i, env in enumerate(self.python_envs_list):
                if env.path == service.python_env.path:
                    self.backend_python_var.set(f"{env.name} ({env.version})")
                    break
    
    def _fill_frontend_detection(self, service):
        """填充前端检测结果"""
        self.frontend_enabled.select()
        self.frontend_name.delete(0, "end")
        self.frontend_name.insert(0, service.name)
        
        self.frontend_tech.delete(0, "end")
        self.frontend_tech.insert(0, service.tech_stack)
        
        self.frontend_cwd.delete(0, "end")
        self.frontend_cwd.insert(0, service.working_dir)
        
        self.frontend_startup.delete(0, "end")
        self.frontend_startup.insert(0, service.startup_file)
        
        self.frontend_cmd.delete(0, "end")
        self.frontend_cmd.insert(0, service.command)
        
        self.frontend_cmd_template.delete(0, "end")
        self.frontend_cmd_template.insert(0, service.command_template)
        
        if service.port_config:
            self.frontend_port.delete(0, "end")
            self.frontend_port.insert(0, str(service.port_config.port))
            
            source_text = f"来源: {service.port_config.port_source} (置信度: {service.port_config.confidence:.0%})"
            self.frontend_port_source.configure(text=source_text)
    
    def _fill_data(self):
        """填充编辑数据"""
        p = self.project
        self.name_entry.insert(0, p.name)
        self.desc_entry.insert(0, p.description)
        self.path_entry.insert(0, p.path)
        
        # 后端服务
        if 'backend' in p.services:
            backend = p.services['backend']
            if backend.enabled:
                self.backend_enabled.select()
            self.backend_name.insert(0, backend.name)
            self.backend_tech.insert(0, backend.tech_stack)
            self.backend_cwd.insert(0, backend.working_dir)
            self.backend_startup.insert(0, backend.startup_file)
            self.backend_cmd.insert(0, backend.command)
            self.backend_cmd_template.insert(0, backend.command_template)
            
            if backend.port_config:
                self.backend_port.insert(0, str(backend.port_config.port))
            
            if backend.python_env:
                for i, env in enumerate(self.python_envs_list):
                    if env.path == backend.python_env.path:
                        self.backend_python_var.set(f"{env.name} ({env.version})")
                        break
        
        # 前端服务
        if 'frontend' in p.services:
            frontend = p.services['frontend']
            if frontend.enabled:
                self.frontend_enabled.select()
            self.frontend_name.insert(0, frontend.name)
            self.frontend_tech.insert(0, frontend.tech_stack)
            self.frontend_cwd.insert(0, frontend.working_dir)
            self.frontend_startup.insert(0, frontend.startup_file)
            self.frontend_cmd.insert(0, frontend.command)
            self.frontend_cmd_template.insert(0, frontend.command_template)
            
            if frontend.port_config:
                self.frontend_port.insert(0, str(frontend.port_config.port))
        
        # 元数据
        if p.metadata.tags:
            self.tags_entry.insert(0, ", ".join(p.metadata.tags))
        self.category_entry.insert(0, p.metadata.category)
        self.priority_var.set(p.metadata.priority)
        self.notes_text.insert("1.0", p.metadata.notes)
    
    def _test_backend_startup(self):
        """测试后端启动"""
        if not self.backend_enabled.get():
            messagebox.showwarning("提示", "请先启用后端服务")
            return
        
        # 获取配置
        cmd = self.backend_cmd.get().strip()
        cwd = self.backend_cwd.get().strip() or self.path_entry.get().strip()
        
        if not cmd:
            messagebox.showwarning("提示", "请先配置启动命令")
            return
        
        if not cwd or not os.path.exists(cwd):
            messagebox.showerror("错误", "工作目录不存在")
            return
        
        # 创建测试窗口
        test_window = ctk.CTkToplevel(self)
        test_window.title("测试启动")
        test_window.geometry("700x500")
        test_window.transient(self)
        test_window.grab_set()
        
        # 标题
        ctk.CTkLabel(
            test_window,
            text="🧪 测试启动后端服务",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=15)
        
        # 信息显示
        info_frame = ctk.CTkFrame(test_window, fg_color="#F5F5F5")
        info_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        ctk.CTkLabel(
            info_frame,
            text=f"命令: {cmd}",
            font=ctk.CTkFont(family="Consolas", size=11),
            anchor="w"
        ).pack(anchor="w", padx=10, pady=5)
        
        ctk.CTkLabel(
            info_frame,
            text=f"目录: {cwd}",
            font=ctk.CTkFont(family="Consolas", size=11),
            anchor="w"
        ).pack(anchor="w", padx=10, pady=(0, 5))
        
        # 日志显示
        log_text = ctk.CTkTextbox(test_window, width=660, height=300, font=ctk.CTkFont(family="Consolas", size=10))
        log_text.pack(padx=20, pady=(0, 10))
        
        # 状态标签
        status_label = ctk.CTkLabel(
            test_window,
            text="⏳ 正在启动...",
            font=ctk.CTkFont(size=12)
        )
        status_label.pack(pady=5)
        
        # 按钮
        btn_frame = ctk.CTkFrame(test_window, fg_color="transparent")
        btn_frame.pack(pady=10)
        
        stop_btn = ctk.CTkButton(
            btn_frame,
            text="停止测试",
            width=120,
            fg_color="#000000",
            hover_color="#333333",
            text_color="#FFFFFF",
            state="disabled"
        )
        stop_btn.pack(side="left", padx=5)
        
        close_btn = ctk.CTkButton(
            btn_frame,
            text="关闭",
            width=120,
            command=test_window.destroy
        )
        close_btn.pack(side="left", padx=5)
        
        test_window.update()
        
        # 启动进程
        import subprocess
        import threading
        import time
        
        process = None
        
        def append_log(text, color=None):
            log_text.insert("end", text + "\n")
            log_text.see("end")
            test_window.update()
        
        def run_test():
            nonlocal process
            try:
                append_log(f"[{time.strftime('%H:%M:%S')}] 启动命令: {cmd}")
                append_log(f"[{time.strftime('%H:%M:%S')}] 工作目录: {cwd}")
                append_log("-" * 80)
                
                # 启动进程
                process = subprocess.Popen(
                    cmd,
                    shell=True,
                    cwd=cwd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    encoding='utf-8',
                    errors='ignore'
                )
                
                stop_btn.configure(state="normal")
                
                # 读取输出（最多10秒）
                start_time = time.time()
                success = False
                error_occurred = False
                
                while time.time() - start_time < 10:
                    line = process.stdout.readline()
                    if line:
                        append_log(line.rstrip())
                        
                        # 检测成功启动的关键词
                        line_lower = line.lower()
                        if any(keyword in line_lower for keyword in ['running', 'started', 'listening', 'uvicorn', 'application startup complete']):
                            success = True
                        
                        # 检测错误
                        if any(keyword in line_lower for keyword in ['error', 'traceback', 'exception', 'failed', 'modulenotfounderror', 'importerror']):
                            error_occurred = True
                    
                    # 检查进程是否还在运行
                    if process.poll() is not None:
                        break
                    
                    time.sleep(0.1)
                
                # 停止进程
                append_log("-" * 80)
                if process.poll() is None:
                    process.terminate()
                    time.sleep(0.5)
                    if process.poll() is None:
                        process.kill()
                    append_log(f"[{time.strftime('%H:%M:%S')}] 进程已停止")
                
                # 显示结果
                if error_occurred:
                    status_label.configure(
                        text="❌ 启动失败 - 检测到错误（可能是Python环境或依赖问题）",
                        text_color="#8E8E93"
                    )
                    append_log("\n⚠️ 建议：检查Python环境是否正确，确认所有依赖已安装")
                elif success:
                    status_label.configure(
                        text="✅ 启动成功 - Python环境和依赖正常",
                        text_color="#8E8E93"
                    )
                    append_log("\n✅ 测试通过！可以安全保存项目配置")
                else:
                    status_label.configure(
                        text="⚠️ 未检测到明确的启动信号 - 请查看日志",
                        text_color="#8E8E93"
                    )
                    append_log("\n💡 提示：如果看到正常输出，说明环境可能没问题")
                
                stop_btn.configure(state="disabled")
                
            except Exception as e:
                append_log(f"\n❌ 测试失败: {e}")
                status_label.configure(
                    text=f"❌ 测试失败: {e}",
                    text_color="#8E8E93"
                )
                stop_btn.configure(state="disabled")
        
        def stop_test():
            nonlocal process
            if process and process.poll() is None:
                process.terminate()
                time.sleep(0.5)
                if process.poll() is None:
                    process.kill()
                append_log(f"[{time.strftime('%H:%M:%S')}] 用户手动停止")
                status_label.configure(text="⏹️ 已停止")
                stop_btn.configure(state="disabled")
        
        stop_btn.configure(command=stop_test)
        
        # 在新线程中运行测试
        thread = threading.Thread(target=run_test, daemon=True)
        thread.start()
    
    def _test_frontend_startup(self):
        """测试前端启动"""
        if not self.frontend_enabled.get():
            messagebox.showwarning("提示", "请先启用前端服务")
            return
        
        # 获取配置
        cmd = self.frontend_cmd.get().strip()
        cwd = self.frontend_cwd.get().strip() or self.path_entry.get().strip()
        
        if not cmd:
            messagebox.showwarning("提示", "请先配置启动命令")
            return
        
        if not cwd or not os.path.exists(cwd):
            messagebox.showerror("错误", "工作目录不存在")
            return
        
        # 创建测试窗口
        test_window = ctk.CTkToplevel(self)
        test_window.title("测试启动")
        test_window.geometry("700x500")
        test_window.transient(self)
        test_window.grab_set()
        
        # 标题
        ctk.CTkLabel(
            test_window,
            text="🧪 测试启动前端服务",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=15)
        
        # 信息显示
        info_frame = ctk.CTkFrame(test_window, fg_color="#F5F5F5")
        info_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        ctk.CTkLabel(
            info_frame,
            text=f"命令: {cmd}",
            font=ctk.CTkFont(family="Consolas", size=11),
            anchor="w"
        ).pack(anchor="w", padx=10, pady=5)
        
        ctk.CTkLabel(
            info_frame,
            text=f"目录: {cwd}",
            font=ctk.CTkFont(family="Consolas", size=11),
            anchor="w"
        ).pack(anchor="w", padx=10, pady=(0, 5))
        
        # 日志显示
        log_text = ctk.CTkTextbox(test_window, width=660, height=300, font=ctk.CTkFont(family="Consolas", size=10))
        log_text.pack(padx=20, pady=(0, 10))
        
        # 状态标签
        status_label = ctk.CTkLabel(
            test_window,
            text="⏳ 正在启动...",
            font=ctk.CTkFont(size=12)
        )
        status_label.pack(pady=5)
        
        # 按钮
        btn_frame = ctk.CTkFrame(test_window, fg_color="transparent")
        btn_frame.pack(pady=10)
        
        stop_btn = ctk.CTkButton(
            btn_frame,
            text="停止测试",
            width=120,
            fg_color="#000000",
            hover_color="#333333",
            text_color="#FFFFFF",
            state="disabled"
        )
        stop_btn.pack(side="left", padx=5)
        
        close_btn = ctk.CTkButton(
            btn_frame,
            text="关闭",
            width=120,
            command=test_window.destroy
        )
        close_btn.pack(side="left", padx=5)
        
        test_window.update()
        
        # 启动进程
        import subprocess
        import threading
        import time
        
        process = None
        
        def append_log(text, color=None):
            log_text.insert("end", text + "\n")
            log_text.see("end")
            test_window.update()
        
        def run_test():
            nonlocal process
            try:
                append_log(f"[{time.strftime('%H:%M:%S')}] 启动命令: {cmd}")
                append_log(f"[{time.strftime('%H:%M:%S')}] 工作目录: {cwd}")
                append_log("-" * 80)
                
                # 启动进程
                process = subprocess.Popen(
                    cmd,
                    shell=True,
                    cwd=cwd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    encoding='utf-8',
                    errors='ignore'
                )
                
                stop_btn.configure(state="normal")
                
                # 读取输出（最多15秒，前端启动可能需要更长时间）
                start_time = time.time()
                success = False
                error_occurred = False
                
                while time.time() - start_time < 15:
                    line = process.stdout.readline()
                    if line:
                        append_log(line.rstrip())
                        
                        # 检测成功启动的关键词
                        line_lower = line.lower()
                        if any(keyword in line_lower for keyword in ['ready', 'compiled', 'local:', 'network:', 'running at', 'server running', 'vite']):
                            success = True
                        
                        # 检测错误
                        if any(keyword in line_lower for keyword in ['error', 'failed', 'cannot find module', 'enoent', 'command not found']):
                            error_occurred = True
                    
                    # 检查进程是否还在运行
                    if process.poll() is not None:
                        break
                    
                    time.sleep(0.1)
                
                # 停止进程
                append_log("-" * 80)
                if process.poll() is None:
                    process.terminate()
                    time.sleep(0.5)
                    if process.poll() is None:
                        process.kill()
                    append_log(f"[{time.strftime('%H:%M:%S')}] 进程已停止")
                
                # 显示结果
                if error_occurred:
                    status_label.configure(
                        text="❌ 启动失败 - 检测到错误（可能是依赖或配置问题）",
                        text_color="#8E8E93"
                    )
                    append_log("\n⚠️ 建议：检查是否已安装依赖（npm install），确认配置文件正确")
                elif success:
                    status_label.configure(
                        text="✅ 启动成功 - 前端环境和依赖正常",
                        text_color="#8E8E93"
                    )
                    append_log("\n✅ 测试通过！可以安全保存项目配置")
                else:
                    status_label.configure(
                        text="⚠️ 未检测到明确的启动信号 - 请查看日志",
                        text_color="#8E8E93"
                    )
                    append_log("\n💡 提示：如果看到正常输出，说明环境可能没问题")
                
                stop_btn.configure(state="disabled")
                
            except Exception as e:
                append_log(f"\n❌ 测试失败: {e}")
                status_label.configure(
                    text=f"❌ 测试失败: {e}",
                    text_color="#8E8E93"
                )
                stop_btn.configure(state="disabled")
        
        def stop_test():
            nonlocal process
            if process and process.poll() is None:
                process.terminate()
                time.sleep(0.5)
                if process.poll() is None:
                    process.kill()
                append_log(f"[{time.strftime('%H:%M:%S')}] 用户手动停止")
                status_label.configure(text="⏹️ 已停止")
                stop_btn.configure(state="disabled")
        
        stop_btn.configure(command=stop_test)
        
        # 在新线程中运行测试
        thread = threading.Thread(target=run_test, daemon=True)
        thread.start()
    
    def _save(self):
        """保存项目"""
        # 验证
        name = self.name_entry.get().strip()
        path = self.path_entry.get().strip()
        
        if not name:
            messagebox.showwarning("提示", "请输入项目名称")
            return
        
        if not path:
            messagebox.showwarning("提示", "请选择项目路径")
            return
        
        if not os.path.exists(path):
            messagebox.showerror("错误", "项目路径不存在")
            return
        
        # 创建项目
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
        if self.backend_enabled.get():
            backend = ServiceConfig(
                enabled=True,
                name=self.backend_name.get().strip() or "后端服务",
                service_type="backend",
                tech_stack=self.backend_tech.get().strip(),
                working_dir=self.backend_cwd.get().strip() or path,
                startup_file=self.backend_startup.get().strip(),
                command=self.backend_cmd.get().strip(),
                command_template=self.backend_cmd_template.get().strip()
            )
            
            # 端口配置
            port_str = self.backend_port.get().strip()
            if port_str:
                try:
                    port = int(port_str)
                    backend.port_config = PortConfig(port=port)
                except ValueError:
                    messagebox.showwarning("提示", "后端端口必须是数字")
                    return
            
            # Python环境
            python_selection = self.backend_python_var.get()
            if python_selection != "不指定":
                for env in self.python_envs_list:
                    if f"{env.name} ({env.version})" == python_selection:
                        backend.python_env = env
                        break
            
            backend.log_file = f"logs/{name}_backend.log"
            project.services['backend'] = backend
        
        # 前端服务
        if self.frontend_enabled.get():
            frontend = ServiceConfig(
                enabled=True,
                name=self.frontend_name.get().strip() or "前端服务",
                service_type="frontend",
                tech_stack=self.frontend_tech.get().strip(),
                working_dir=self.frontend_cwd.get().strip() or path,
                startup_file=self.frontend_startup.get().strip(),
                command=self.frontend_cmd.get().strip(),
                command_template=self.frontend_cmd_template.get().strip()
            )
            
            # 端口配置
            port_str = self.frontend_port.get().strip()
            if port_str:
                try:
                    port = int(port_str)
                    frontend.port_config = PortConfig(port=port)
                except ValueError:
                    messagebox.showwarning("提示", "前端端口必须是数字")
                    return
            
            frontend.log_file = f"logs/{name}_frontend.log"
            project.services['frontend'] = frontend
        
        # 元数据
        tags_str = self.tags_entry.get().strip()
        tags = [t.strip() for t in tags_str.split(",")] if tags_str else []
        
        project.metadata = ProjectMetadata(
            tags=tags,
            category=self.category_entry.get().strip(),
            priority=self.priority_var.get(),
            notes=self.notes_text.get("1.0", "end").strip()
        )
        
        # 保存
        if self.is_edit:
            enhanced_project_manager.update(project)
        else:
            enhanced_project_manager.add(project)
        
        if self.on_save:
            self.on_save()
        
        self.destroy()
