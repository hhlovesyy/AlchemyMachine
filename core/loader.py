# core/loader.py
import importlib
import inspect
import sys
import os
import yaml
from .base import BaseModule # 导入上面改好的基类

def load_config(path="app_config.yaml"):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def load_active_modules(config):
    loaded_instances = {}
    
    # 把当前目录加入 path 方便 import
    if os.getcwd() not in sys.path:
        sys.path.append(os.getcwd())

    for key, settings in config.get('modules', {}).items():
        if not settings.get('enable', False):
            continue

        filename = settings.get('file')
        module_import_path = f"modules.{filename[:-3]}"
        
        try:
            lib = importlib.import_module(module_import_path)
            
            # 寻找继承自 BaseModule 的类
            target_class = None
            for name, obj in inspect.getmembers(lib, inspect.isclass):
                if issubclass(obj, BaseModule) and obj is not BaseModule:
                    target_class = obj
                    break
            
            if target_class:
                # === 实例化 ===
                instance = target_class()
                
                # === 关键：注入配置 ===
                # 如果yaml里配了name/icon，就用yaml的，否则用代码里写的
                if 'name' in settings:
                    instance.name = settings['name']
                if 'icon' in settings:
                    instance.icon = settings['icon']
                
                # 使用配置里的 key 作为菜单名 (或者 settings['name'])
                menu_name = f"{instance.icon} {instance.name}"
                loaded_instances[menu_name] = instance
                
        except Exception as e:
            print(f"❌ 加载 {filename} 失败: {e}")

    return loaded_instances