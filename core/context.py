# core/context.py
import os
import yaml
import streamlit as st

class GlobalContext:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GlobalContext, cls).__new__(cls)
            cls._instance.init_context()
        return cls._instance

    def init_context(self):
        # 加载全局配置，解耦硬编码路径
        # 实际项目中建议从 external config 加载
        self.root_dir = "/root/autodl-tmp/MyRepository/MCM-LDM"
        self.config_dir = os.path.join(self.root_dir, "configs")
        self.base_yaml_path = os.path.join(self.config_dir, "yaml_task_base.yaml")
        self.assets_file = os.path.join(self.config_dir, "assets.yaml")
        self.state_file = os.path.join(self.root_dir, "alchemy_state.json")
        
        # 确保目录存在
        os.makedirs(os.path.join(self.root_dir, "experiments", "mld"), exist_ok=True)

    def get_path(self, *subpaths):
        """类似 os.path.join，但是基于 ROOT_DIR"""
        return os.path.join(self.root_dir, *subpaths)

    # 简单的状态持久化封装
    def set_state(self, key, value):
        st.session_state[key] = value
        # 这里可以加入写入 json 文件的逻辑
    
    def get_state(self, key, default=None):
        return st.session_state.get(key, default)