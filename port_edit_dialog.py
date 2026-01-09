"""端口编辑对话框 - 直接修改配置文件中的端口"""
import customtkinter as ctk
from tkinter import messagebox
import os
import json
import re
from typing import Optional
from enhanced_models import Project, ServiceConfig, enhanced_project_manager
from port_detector import port_detector


class PortEditDialog(ctk.CTkToplevel):
    """端口编辑对话框"""
    
    def __init__(self, master, project: Project, service_key: str, service: ServiceConfig):
        super().__init__(master)
        self.project = project
        self.service_key = service_key
        self.service = service
        self.project_manager = enhanced_project_manager
        
        self.title(f"修改端口 - {service.name or service_key}")
        self.geometry("600x500")
        self.configure(fg_color="#FAFAFA")
        
        self.transient(master)
        self.grab_set()
        
        # 标题
        title_label = ctk.CTkLabel(
            self,
            text=f"🔧 修改 {service.name or service_key} 端口",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_label.pack(pady=(20, 10))
        
        # 当前端口信息
        info_frame = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=8, border_width=1, border_color="#E5E5E5")
        info_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        # 兼容新旧ServiceConfig
        current_port = getattr(service, 'port', None) or (service.port_config.port if hasattr(service, 'port_config') and service.port_config else None)
        original_port = None
        if hasattr(service, 'port_config') and service.port_config:
            original_port = service.port_config.original_port
        
        # 如果original_port为空，尝试重新检测端口作为原始端口
        if original_port is None:
            project_path = self.project.path
            if self.service_key == "frontend":
                result = port_detector.detect_frontend_port(project_path)
            else:
                result = port_detector.detect_backend_port(project_path)
            
            if result and result.port:
                original_port = result.port
                # 保存检测到的原始端口
                if hasattr(service, 'port_config') and service.port_config:
                    service.port_config.original_port = original_port
                    self.project_manager.update(self.project)
        
        # 始终显示原始端口和当前端口
        if original_port:
            ctk.CTkLabel(
                info_frame,
                text=f"原始端口: {original_port}",
                font=ctk.CTkFont(size=13),
                text_color="#8E8E93"
            ).pack(pady=(10, 2), padx=15, anchor="w")
            
            # 如果端口被修改过，用不同颜色标识
            if original_port != current_port:
                port_color = "#FF6B6B"  # 红色表示已修改
                port_text = f"当前端口: {current_port} (已修改)"
            else:
                port_color = "#000000"
                port_text = f"当前端口: {current_port}"
            
            ctk.CTkLabel(
                info_frame,
                text=port_text,
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=port_color
            ).pack(pady=(2, 5), padx=15, anchor="w")
        else:
            # 如果没有原始端口信息，只显示当前端口
            ctk.CTkLabel(
                info_frame,
                text=f"当前端口: {current_port}",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color="#000000"
            ).pack(pady=(10, 5), padx=15, anchor="w")
        
        # 检测端口来源
        port_result = self._detect_port_source()
        if port_result:
            ctk.CTkLabel(
                info_frame,
                text=f"来源: {port_result['source']}",
                font=ctk.CTkFont(size=12),
                text_color="#8E8E93"
            ).pack(pady=(0, 5), padx=15, anchor="w")
            
            if port_result['file_path']:
                ctk.CTkLabel(
                    info_frame,
                    text=f"文件: {port_result['file_path']}",
                    font=ctk.CTkFont(size=11, family="Consolas"),
                    text_color="#8E8E93"
                ).pack(pady=(0, 10), padx=15, anchor="w")
        
        # 新端口输入
        input_frame = ctk.CTkFrame(self, fg_color="transparent")
        input_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        ctk.CTkLabel(
            input_frame,
            text="新端口:",
            font=ctk.CTkFont(size=13)
        ).pack(side="left", padx=(0, 10))
        
        self.new_port_entry = ctk.CTkEntry(
            input_frame,
            width=150,
            height=35,
            font=ctk.CTkFont(size=14)
        )
        self.new_port_entry.pack(side="left")
        self.new_port_entry.insert(0, str(current_port) if current_port else "")
        self.current_port = current_port
        
        # 修改方式选择
        method_frame = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=8, border_width=1, border_color="#E5E5E5")
        method_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        ctk.CTkLabel(
            method_frame,
            text="修改方式:",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#000000"
        ).pack(pady=(15, 10), padx=15, anchor="w")
        
        self.method_var = ctk.StringVar(value="devmanager")
        
        # 选项1: 只修改 DevManager 配置 (推荐)
        devmanager_radio = ctk.CTkRadioButton(
            method_frame,
            text="只修改 DevManager 配置 (推荐)",
            variable=self.method_var,
            value="devmanager",
            font=ctk.CTkFont(size=12)
        )
        devmanager_radio.pack(pady=(0, 5), padx=20, anchor="w")
        
        ctk.CTkLabel(
            method_frame,
            text="不修改项目源码，只在 DevManager 中记录新端口",
            font=ctk.CTkFont(size=11),
            text_color="#8E8E93"
        ).pack(pady=(0, 15), padx=40, anchor="w")
        
        # 选项2: 修改配置文件
        config_radio = ctk.CTkRadioButton(
            method_frame,
            text="修改配置文件",
            variable=self.method_var,
            value="config",
            font=ctk.CTkFont(size=12)
        )
        config_radio.pack(pady=(0, 5), padx=20, anchor="w")
        
        ctk.CTkLabel(
            method_frame,
            text="直接修改 vite.config.js、.env、main.py 等配置文件",
            font=ctk.CTkFont(size=11),
            text_color="#8E8E93"
        ).pack(pady=(0, 15), padx=40, anchor="w")
        
        # 警告提示
        warning_label = ctk.CTkLabel(
            self,
            text="⚠️ 修改配置文件会直接修改项目源码，请确保已备份",
            font=ctk.CTkFont(size=11),
            text_color="#666666"
        )
        warning_label.pack(pady=(0, 20))
        
        # 按钮
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        ctk.CTkButton(
            btn_frame,
            text="取消",
            width=100,
            height=35,
            fg_color="#FFFFFF",
            hover_color="#F5F5F5",
            text_color="#000000",
            border_width=1,
            border_color="#E5E5E5",
            command=self.destroy
        ).pack(side="right", padx=(10, 0))
        
        ctk.CTkButton(
            btn_frame,
            text="确认修改",
            width=120,
            height=35,
            fg_color="#000000",
            hover_color="#333333",
            text_color="#FFFFFF",
            command=self.apply_changes
        ).pack(side="right")
    
    def _detect_port_source(self) -> Optional[dict]:
        """检测端口来源"""
        project_path = self.project.path
        
        if self.service_key == "frontend":
            result = port_detector.detect_frontend_port(project_path)
        else:
            result = port_detector.detect_backend_port(project_path)
        
        service_port = getattr(self.service, 'port', None) or (self.service.port_config.port if hasattr(self.service, 'port_config') and self.service.port_config else None)
        if result.port == service_port:
            # 找到配置文件
            file_path = None
            if result.source and result.source != "智能建议":
                # 尝试找到完整文件路径
                possible_files = [
                    "vite.config.js", "vite.config.ts",
                    "package.json", ".env", ".env.local",
                    "vue.config.js", "webpack.config.js",
                    "main.py", "app.py", "server.js"
                ]
                for f in possible_files:
                    full_path = os.path.join(project_path, f)
                    if os.path.exists(full_path) and f in result.source:
                        file_path = full_path
                        break
            
            return {
                "source": result.source,
                "file_path": file_path,
                "confidence": result.confidence
            }
        
        return None
    
    def apply_changes(self):
        """应用修改"""
        new_port_str = self.new_port_entry.get().strip()
        
        if not new_port_str.isdigit():
            messagebox.showerror("错误", "端口必须是数字")
            return
        
        new_port = int(new_port_str)
        
        if new_port < 1 or new_port > 65535:
            messagebox.showerror("错误", "端口范围必须在 1-65535 之间")
            return
        
        if new_port == self.current_port:
            messagebox.showinfo("提示", "端口未改变")
            return
        
        method = self.method_var.get()
        
        if method == "config":
            # 修改配置文件
            success = self._modify_config_file(new_port)
            if success:
                # 同时更新 DevManager 配置
                self._update_devmanager_config(new_port)
                messagebox.showinfo("成功", f"端口已修改为 {new_port}\n\n配置文件已更新")
                self.destroy()
            else:
                messagebox.showerror("失败", "无法自动修改配置文件\n\n请手动修改或选择「只修改 DevManager 配置」")
        else:
            # 只修改 DevManager 配置
            self._update_devmanager_config(new_port)
            messagebox.showinfo("成功", f"DevManager 配置已更新为端口 {new_port}\n\n注意: 项目配置文件未修改，启动时可能仍使用旧端口")
            self.destroy()
    
    def _modify_config_file(self, new_port: int) -> bool:
        """修改配置文件"""
        project_path = self.project.path
        
        # 尝试修改各种配置文件
        modified = False
        
        # 1. 修改 .env 文件
        for env_file in ['.env', '.env.local', '.env.development']:
            env_path = os.path.join(project_path, env_file)
            if os.path.exists(env_path):
                if self._modify_env_file(env_path, new_port):
                    modified = True
        
        # 2. 修改 vite.config.js/ts
        for config_file in ['vite.config.js', 'vite.config.ts']:
            config_path = os.path.join(project_path, config_file)
            if os.path.exists(config_path):
                if self._modify_vite_config(config_path, new_port):
                    modified = True
        
        # 3. 修改 Python 文件
        if self.service_key == "backend":
            for py_file in ['main.py', 'app.py', 'run.py']:
                py_path = os.path.join(project_path, py_file)
                if os.path.exists(py_path):
                    if self._modify_python_file(py_path, new_port):
                        modified = True
        
        return modified
    
    def _modify_env_file(self, file_path: str, new_port: int) -> bool:
        """修改 .env 文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 替换 PORT=xxx
            new_content = re.sub(
                r'^(PORT|VITE_PORT|REACT_APP_PORT|VUE_APP_PORT)\s*=\s*\d+',
                f'\\1={new_port}',
                content,
                flags=re.MULTILINE
            )
            
            if new_content != content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                return True
            
            return False
        except Exception as e:
            print(f"修改 .env 文件失败: {e}")
            return False
    
    def _modify_vite_config(self, file_path: str, new_port: int) -> bool:
        """修改 vite.config.js/ts"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 替换 port: xxxx
            new_content = re.sub(
                r'port\s*:\s*\d+',
                f'port: {new_port}',
                content
            )
            
            if new_content != content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                return True
            
            return False
        except Exception as e:
            print(f"修改 Vite 配置失败: {e}")
            return False
    
    def _modify_python_file(self, file_path: str, new_port: int) -> bool:
        """修改 Python 文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 替换 port=xxxx
            new_content = re.sub(
                r'port\s*=\s*\d+',
                f'port={new_port}',
                content
            )
            
            if new_content != content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                return True
            
            return False
        except Exception as e:
            print(f"修改 Python 文件失败: {e}")
            return False
    
    def _update_devmanager_config(self, new_port: int):
        """更新 DevManager 配置"""
        # 更新服务端口（兼容新旧结构）
        if hasattr(self.service, 'port_config') and self.service.port_config:
            # 如果是第一次修改端口，保存原始端口
            if self.service.port_config.original_port is None:
                self.service.port_config.original_port = self.service.port_config.port
            self.service.port_config.port = new_port
        else:
            self.service.port = new_port
        
        # 保存到配置文件
        self.project_manager.update(self.project)
        
        # 刷新父窗口显示
        if hasattr(self.master, 'refresh_display'):
            self.master.after(100, self.master.refresh_display)
