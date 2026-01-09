"""增强的日志系统 - 确保日志完整记录"""
import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Optional
import threading


class EnhancedLogger:
    """增强的日志管理器"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        self.loggers = {}
        self.lock = threading.Lock()
        
        # 确保日志目录存在
        os.makedirs(log_dir, exist_ok=True)
    
    def get_logger(self, name: str, log_file: str, level: str = "INFO") -> logging.Logger:
        """获取或创建日志记录器"""
        with self.lock:
            if name in self.loggers:
                return self.loggers[name]
            
            # 创建日志记录器
            logger = logging.getLogger(name)
            logger.setLevel(getattr(logging, level.upper(), logging.INFO))
            logger.handlers.clear()
            
            # 确保日志文件路径存在
            log_path = os.path.join(self.log_dir, log_file)
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            
            # 文件处理器（带轮转）
            file_handler = RotatingFileHandler(
                log_path,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)
            
            # 格式化
            formatter = logging.Formatter(
                '%(asctime)s [%(levelname)s] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            
            logger.addHandler(file_handler)
            self.loggers[name] = logger
            
            return logger
    
    def log_service_start(self, project_name: str, service_name: str, command: str, log_file: str):
        """记录服务启动"""
        logger = self.get_logger(f"{project_name}_{service_name}", log_file)
        logger.info("=" * 60)
        logger.info(f"服务启动: {service_name}")
        logger.info(f"项目: {project_name}")
        logger.info(f"启动命令: {command}")
        logger.info(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)
    
    def log_service_stop(self, project_name: str, service_name: str, log_file: str):
        """记录服务停止"""
        logger = self.get_logger(f"{project_name}_{service_name}", log_file)
        logger.info("=" * 60)
        logger.info(f"服务停止: {service_name}")
        logger.info(f"停止时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)
    
    def log_service_output(self, project_name: str, service_name: str, output: str, log_file: str, is_error: bool = False):
        """记录服务输出"""
        logger = self.get_logger(f"{project_name}_{service_name}", log_file)
        
        # 分行记录
        for line in output.strip().split('\n'):
            if line.strip():
                if is_error:
                    logger.error(line)
                else:
                    logger.info(line)
    
    def log_service_error(self, project_name: str, service_name: str, error: str, log_file: str):
        """记录服务错误"""
        logger = self.get_logger(f"{project_name}_{service_name}", log_file)
        logger.error("=" * 60)
        logger.error(f"服务错误: {service_name}")
        logger.error(f"错误时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.error(f"错误信息: {error}")
        logger.error("=" * 60)
    
    def get_log_content(self, log_file: str, max_lines: int = 1000) -> str:
        """获取日志内容"""
        log_path = os.path.join(self.log_dir, log_file)
        
        if not os.path.exists(log_path):
            return "日志文件不存在"
        
        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                # 返回最后N行
                return ''.join(lines[-max_lines:])
        except Exception as e:
            return f"读取日志失败: {e}"
    
    def clear_log(self, log_file: str):
        """清空日志"""
        log_path = os.path.join(self.log_dir, log_file)
        try:
            if os.path.exists(log_path):
                with open(log_path, 'w', encoding='utf-8') as f:
                    f.write("")
        except Exception as e:
            print(f"清空日志失败: {e}")
    
    def get_all_logs(self) -> list:
        """获取所有日志文件"""
        logs = []
        for root, dirs, files in os.walk(self.log_dir):
            for file in files:
                if file.endswith('.log'):
                    log_path = os.path.join(root, file)
                    rel_path = os.path.relpath(log_path, self.log_dir)
                    size = os.path.getsize(log_path)
                    mtime = os.path.getmtime(log_path)
                    logs.append({
                        'path': rel_path,
                        'size': size,
                        'modified': datetime.fromtimestamp(mtime)
                    })
        return logs


# 全局实例
enhanced_logger = EnhancedLogger()
