import streamlit as st
import os
from core.base import BaseModule
from core.process_mgr import ProcessManager
import time

class OmniControlAndMotionLCMRunner(BaseModule):
    def render_sidebar(self):
        st.subheader("⚙️ OmniControl 运行参数")
        
        # 参数配置
        self.model_path = st.text_input(
            "Model Path", 
            value="./save/omnicontrol_ckpt/model_humanml3d.pt"
        )
        self.num_reps = st.number_input("Num Repetitions", value=1, min_value=1)
        self.gpu_id = st.text_input("GPU ID", "0")

        st.subheader("MotionLCM 运行参数")
        self.motionlcm_yaml_path = st.text_input(
            "MotionLCM Config YAML Path", 
            value="configs/motionlcm_control_s.yaml"
        )

        # 是/否
        self.user_define_hint = st.toggle(
            "Enable User Define Hint", 
            value=False, 
            key="motionlcm_user_define_hint"
        )

    def render_main(self):
        # 固定工作目录
        OMNI_WORK_DIR = "/root/autodl-tmp/MyRepository/OmniControl/OmniControl"
        LCM_WORK_DIR = "/root/autodl-tmp/MyRepository/MotionLCM/MotionLCM"
        
        st.info(f"📍 OmniControl 工作目录: `{OMNI_WORK_DIR}`")
        st.info(f"📍 MotionLCM 工作目录: `{LCM_WORK_DIR}`")
        
        # 构造命令
        cmd = (
            f"CUDA_VISIBLE_DEVICES={self.gpu_id} "
            f"python -m sample.generate "
            f"--model_path {self.model_path} "
            f"--num_repetitions {self.num_reps}"
        )
        
        st.markdown("### 🖥️ OmniControl 待执行命令")
        st.code(f"cd {OMNI_WORK_DIR}\n{cmd}", language="bash")

        st.markdown("### 🖥️ MotionLCM 待执行命令")
        st.code(f"cd {LCM_WORK_DIR}\nCUDA_VISIBLE_DEVICES={self.gpu_id} python demo.py --cfg {self.motionlcm_yaml_path}", language="bash")
        
        st.divider()
        
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("🚀 立即运行 OmniControl", type="primary"):
                if not os.path.exists(OMNI_WORK_DIR):
                    st.error(f"❌ 找不到目录: {OMNI_WORK_DIR}")
                    return
                
                # 这里的 Session Name 可以加时间戳防止重复
                session_name = "omni_gen_task"
                
                # 调用核心层的 ProcessManager
                # 注意：run_in_screen 内部封装了 screen -dmS ...
                success, msg = ProcessManager.run_with_log(
                    command=cmd, 
                    task_name=session_name, 
                    root_dir=OMNI_WORK_DIR
                )
                
                if success:
                    # 1. 保存路径
                    self.set_state("last_log_path", msg)
                    # 2. 弹窗提示
                    st.toast(f"Omni任务启动！正在监听日志: {os.path.basename(msg)}")
                    # 3. 🔥🔥 核心：强制刷新页面 🔥🔥
                    # 这样下方的 render_log_monitor 才能立即拿到新的路径并显示
                    time.sleep(0.5) # 稍微等一下文件系统
                    st.rerun()
                else:
                    st.error(f"启动失败: {msg}")
        
        with col2:
            if st.button("🚀 立即运行 MotionLCM", type="primary"):
                if not os.path.exists(LCM_WORK_DIR):
                    st.error(f"❌ 找不到目录: {LCM_WORK_DIR}")
                    return
                
                # 这里的 Session Name 可以加时间戳防止重复
                session_name_lcm = "motionlcm_gen_task"

                motionlcm_cmd = (
                    f"CUDA_VISIBLE_DEVICES={self.gpu_id} "
                    f"python demo.py "
                    f"--cfg {self.motionlcm_yaml_path} "
                    f"--user_define_hint {self.user_define_hint}"
                )
                
                
                
                # 调用核心层的 ProcessManager
                # 注意：run_in_screen 内部封装了 screen -dmS ...
                success, msg = ProcessManager.run_with_log(
                    command=motionlcm_cmd, 
                    task_name=session_name_lcm, 
                    root_dir=LCM_WORK_DIR
                )
                
                if success:
                    # 1. 保存路径
                    self.set_state("last_log_path", msg)
                    # 2. 弹窗提示
                    st.toast(f"MotionLCM任务启动！正在监听日志: {os.path.basename(msg)}")
                    # 3. 🔥🔥 核心：强制刷新页面 🔥🔥
                    # 这样下方的 render_log_monitor 才能立即拿到新的路径并显示
                    time.sleep(0.5) # 稍微等一下文件系统
                    st.rerun()
                else:
                    st.error(f"启动失败: {msg}")

        # 下方显示简单的日志或帮助
        with st.expander("查看如何监控OmniControl运行进度"):
            st.markdown(f"""
            任务正在后台运行。
            1. 点击左侧导航栏的 **"💻 后台进程"** 查看状态。
            2. 或者在终端运行: `screen -r omni_gen_task`
            """)
        with st.expander("查看如何监控MotionLCM运行进度"):
            st.markdown(f"""
            任务正在后台运行。
            1. 点击左侧导航栏的 **"💻 后台进程"** 查看状态。
            2. 或者在终端运行: `screen -r motionlcm_gen_task`
            """)
        self.render_log_monitor()
       