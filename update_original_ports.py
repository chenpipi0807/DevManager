"""批量更新所有项目的原始端口"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from enhanced_models import enhanced_project_manager
from port_detector import port_detector

def update_all_original_ports():
    """批量更新所有项目的原始端口"""
    projects = enhanced_project_manager.get_all()
    updated_count = 0
    
    for project in projects:
        print(f"\n处理项目: {project.name}")
        
        for service_key, service in project.services.items():
            if not service.enabled:
                continue
            
            # 检查是否需要更新original_port
            if hasattr(service, 'port_config') and service.port_config:
                if service.port_config.original_port is None:
                    print(f"  检测 {service_key} 服务端口...")
                    
                    # 检测端口
                    if service_key == "frontend" or "frontend" in service.name.lower():
                        result = port_detector.detect_frontend_port(project.path)
                    else:
                        result = port_detector.detect_backend_port(project.path)
                    
                    if result and result.port:
                        service.port_config.original_port = result.port
                        print(f"    ✓ 设置原始端口: {result.port}")
                        updated_count += 1
                    else:
                        # 如果检测失败，使用当前端口作为原始端口
                        service.port_config.original_port = service.port_config.port
                        print(f"    ✓ 使用当前端口作为原始端口: {service.port_config.port}")
                        updated_count += 1
                else:
                    print(f"  {service_key} 服务已有原始端口: {service.port_config.original_port}")
        
        # 保存项目
        enhanced_project_manager.update(project)
    
    print(f"\n完成！共更新 {updated_count} 个服务的原始端口")

if __name__ == "__main__":
    update_all_original_ports()
