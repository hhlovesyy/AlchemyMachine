# modules/inference.py
import streamlit as st
from core.base import BaseModule

class InferenceModule(BaseModule):
    def __init__(self):
        super().__init__()
        self.name = "推理模式 (Inference)"
        self.icon = "🔮"

    def render_sidebar(self):
        pass

    def render_main(self):
        st.info("这里是重构后的推理模块，可以像 TrainingModule 一样填充逻辑。")
        # 这里你可以把原来的 dirty hack 逻辑封装成一个 clean function
        # 例如 self._inject_code(value)