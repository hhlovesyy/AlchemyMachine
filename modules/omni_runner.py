import streamlit as st
import os
from core.base import BaseModule
from core.process_mgr import ProcessManager

class OmniControlRunner(BaseModule):
    def render_sidebar(self):
        st.subheader("⚙️ 运行参数")
        
        # 参数配置
        self.model_path = st.text_input(
            "Model Path", 
            value="./save/omnicontrol_ckpt/model_humanml3d.pt"
        )
        self.num_reps = st.number_input("Num Repetitions", value=1, min_value=1)
        self.gpu_id = st.text_input("GPU ID", "0")

    def render_main(self):
        # 固定工作目录
        WORK_DIR = "/root/autodl-tmp/MyRepository/OmniControl/OmniControl"
        
        st.info(f"📍 工作目录: `{WORK_DIR}`")
        
        # 构造命令
        cmd = (
            f"CUDA_VISIBLE_DEVICES={self.gpu_id} "
            f"python -m sample.generate "
            f"--model_path {self.model_path} "
            f"--num_repetitions {self.num_reps}"
        )
        
        st.markdown("### 🖥️ 待执行命令")
        st.code(f"cd {WORK_DIR}\n{cmd}", language="bash")
        
        st.divider()
        
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("🚀 立即运行", type="primary"):
                if not os.path.exists(WORK_DIR):
                    st.error(f"❌ 找不到目录: {WORK_DIR}")
                    return
                
                # 这里的 Session Name 可以加时间戳防止重复
                session_name = "omni_gen_task"
                
                # 调用核心层的 ProcessManager
                # 注意：run_in_screen 内部封装了 screen -dmS ...
                success, msg = ProcessManager.run_in_screen(
                    command=cmd, 
                    session_name=session_name, 
                    root_dir=WORK_DIR
                )
                
                if success:
                    st.success("✅ 任务已后台启动！")
                    st.toast(f"Session: {session_name}")
                else:
                    st.error(f"启动失败: {msg}")

        # 下方显示简单的日志或帮助
        with st.expander("查看如何监控进度"):
            st.markdown(f"""
            任务正在后台运行。
            1. 点击左侧导航栏的 **"💻 后台进程"** 查看状态。
            2. 或者在终端运行: `screen -r omni_gen_task`
            """)