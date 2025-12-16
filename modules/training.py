# modules/training.py
import streamlit as st
from core.base import BaseModule

class TrainingModule(BaseModule):
    # __init__ 里不需要设 name 了，全靠 yaml 配置
    
    def render_sidebar(self):
        # 注意：这里不需要写 st.sidebar.xxx
        # 因为基类已经把它包在 with st.sidebar: 里了
        st.info("这里是侧边栏配置区")
        self.batch_size = st.number_input("Batch Size", 32)
        self.lr = st.text_input("Learning Rate", "1e-4")
        if st.button("更新配置"):
            st.toast("配置已更新")

    def render_main(self):
        st.success(f"当前 Batch Size: {getattr(self, 'batch_size', 32)}")
        st.write("这里是主工作区，可以放监控图表、日志输出等...")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("显存占用", "12GB", "+1.2GB")
        with col2:
            if st.button("开始炼丹", type="primary"):
                st.write("启动进程中...")