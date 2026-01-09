"""配置迁移工具 - 从旧版本迁移到v2.0"""
import os
import json
from enhanced_models import (
    Project, ServiceConfig, PortConfig, PythonEnvironment,
    ProjectMetadata, EnhancedProjectManager
)
from port_detector import port_detector


def migrate_old_projects():
    """迁移旧版本项目配置"""
    old_config_file = os.path.join(os.path.dirname(__file__), "projects.json")
    
    if not os.path.exists(old_config_file):
        print("未找到旧配置文件，无需迁移")
        return
    
    print("=" * 60)
    print("开始迁移旧版本项目配置到 v2.0")
    print("=" * 60)
    
    try:
        with open(old_config_file, "r", encoding="utf-8") as f:
            old_data = json.load(f)
        
        manager = EnhancedProjectManager()
        migrated_count = 0
        
        for old_project in old_data.get("projects", []):
            print(f"\n正在迁移项目: {old_project.get('name', '未命名')}")
            
            # 创建新项目
            project = Project(
                id=old_project.get("id"),
                name=old_project.get("name", ""),
                description=old_project.get("description", ""),
                path=old_project.get("path", ""),
                created_at=old_project.get("created_at")
            )
            
            # 迁移服务配置
            for service_key, old_service in old_project.get("services", {}).items():
                print(f"  - 迁移服务: {service_key}")
                
                service = ServiceConfig(
                    enabled=old_service.get("enabled", True),
                    name=old_service.get("name", service_key),
                    working_dir=old_service.get("cwd", ""),
                    command=old_service.get("command", ""),
                    env_vars=old_service.get("env", {}),
                    auto_detected=True
                )
                
                # 判断服务类型
                if "frontend" in service_key.lower() or "front" in service_key.lower():
                    service.service_type = "frontend"
                elif "backend" in service_key.lower() or "back" in service_key.lower() or "api" in service_key.lower():
                    service.service_type = "backend"
                else:
                    service.service_type = "service"
                
                # 迁移端口配置
                if old_service.get("port"):
                    port = old_service["port"]
                    service.port_config = PortConfig(
                        port=port,
                        detected_port=port,
                        port_source="旧配置迁移",
                        confidence=0.5
                    )
                    
                    # 尝试重新检测端口来源
                    if service.working_dir and os.path.exists(service.working_dir):
                        try:
                            detection_result = port_detector.detect_port(service.working_dir)
                            if detection_result and detection_result.port == port:
                                service.port_config.port_source = detection_result.source
                                service.port_config.port_source_file = detection_result.details
                                service.port_config.confidence = detection_result.confidence
                                print(f"    ✓ 重新检测到端口来源: {detection_result.source}")
                        except:
                            pass
                
                # 检测技术栈
                cmd = service.command.lower()
                if "vite" in cmd:
                    service.tech_stack = "vite"
                elif "react" in cmd or "create-react-app" in cmd:
                    service.tech_stack = "react"
                elif "vue" in cmd:
                    service.tech_stack = "vue"
                elif "uvicorn" in cmd or "fastapi" in cmd:
                    service.tech_stack = "fastapi"
                elif "flask" in cmd:
                    service.tech_stack = "flask"
                elif "django" in cmd:
                    service.tech_stack = "django"
                
                # 检测Python环境（后端服务）
                if service.service_type == "backend" and "python" in cmd:
                    # 尝试从命令中提取Python路径
                    import re
                    python_match = re.search(r'([A-Za-z]:[^\s]+python\.exe)', cmd)
                    if python_match:
                        python_path = python_match.group(1)
                        service.python_env = PythonEnvironment(
                            path=python_path,
                            name="检测到的环境"
                        )
                        
                        # 尝试获取版本
                        try:
                            import subprocess
                            result = subprocess.run(
                                [python_path, "--version"],
                                capture_output=True,
                                text=True,
                                timeout=3
                            )
                            if result.returncode == 0:
                                version = result.stdout.strip() or result.stderr.strip()
                                service.python_env.version = version
                                service.python_env.is_conda = "anaconda" in python_path.lower() or "miniconda" in python_path.lower()
                                print(f"    ✓ 检测到Python环境: {version}")
                        except:
                            pass
                
                # 设置日志文件
                service.log_file = f"logs/{project.name}_{service_key}.log"
                
                project.services[service_key] = service
            
            # 设置项目元数据
            project.metadata = ProjectMetadata(
                status="active",
                notes="从旧版本自动迁移"
            )
            
            # 保存项目
            manager.add(project)
            migrated_count += 1
            print(f"  ✓ 项目迁移完成")
        
        print("\n" + "=" * 60)
        print(f"迁移完成！共迁移 {migrated_count} 个项目")
        print(f"新配置文件: projects_v2.json")
        print(f"旧配置文件已保留: projects.json")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def clear_all_projects():
    """清空所有项目配置"""
    print("\n⚠️  警告：此操作将删除所有项目配置！")
    confirm = input("请输入 'YES' 确认删除: ")
    
    if confirm == "YES":
        manager = EnhancedProjectManager()
        count = len(manager.projects)
        manager.projects.clear()
        manager.save()
        print(f"✓ 已删除 {count} 个项目配置")
        return True
    else:
        print("操作已取消")
        return False


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--clear":
        clear_all_projects()
    else:
        migrate_old_projects()
