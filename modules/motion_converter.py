import streamlit as st
import os
from core.base import BaseModule
from core.process_mgr import ProcessManager
import time

class MotionConverter(BaseModule):
    def render_sidebar(self):
        st.subheader("📂 数据选择器")
        
        # 1. 路径导航状态
        default_root = "/root/autodl-tmp"
        current_path = self.get_state("nav_path", default_root)
        
        if not os.path.exists(current_path):
            current_path = default_root
            self.set_state("nav_path", current_path)

        # 2. 显示当前路径 & 返回按钮
        st.caption("当前浏览路径:")
        st.code(current_path, language="bash")
        
        col_up, col_root = st.columns([2, 1])
        with col_up:
            if st.button("⬆️ 上一级", use_container_width=True):
                self.set_state("nav_path", os.path.dirname(current_path))
                st.rerun()
        with col_root:
            if st.button("🏠 根目录", use_container_width=True):
                self.set_state("nav_path", default_root)
                st.rerun()

        st.divider()

        # 3. 核心功能：设置输入目标
        # 按钮 A：将当前浏览的文件夹设为输入（批量模式）
        if st.button("📂 选中当前文件夹作为输入 (Batch)", type="primary", use_container_width=True):
            self.set_state("target_path", current_path)
            self.set_state("target_type", "dir")
            st.toast(f"已选中文件夹: {os.path.basename(current_path)}")

        st.write("--- 或者点击下方文件 ---")

        # 4. 文件列表
        try:
            items = sorted(os.listdir(current_path))
            # 分离文件夹和npy文件
            dirs = [d for d in items if os.path.isdir(os.path.join(current_path, d)) and not d.startswith('.')]
            files = [f for f in items if f.endswith('.npy')]

            with st.container(height=400):
                # 渲染文件夹（用于导航）
                for d in dirs:
                    if st.button(f"📁 {d}", key=f"nav_{d}"):
                        self.set_state("nav_path", os.path.join(current_path, d))
                        st.rerun()
                
                # 渲染文件（用于选择）
                for f in files:
                    if st.button(f"📄 {f}", key=f"sel_{f}"):
                        full_path = os.path.join(current_path, f)
                        self.set_state("target_path", full_path)
                        self.set_state("target_type", "file")
                        st.toast(f"已选中文件: {f}")

        except Exception as e:
            st.error(f"读取目录失败: {e}")

    def render_main(self):
        st.header("⚙️ HumanML3D 数据转换工厂")
        
        # 1. 获取选中的目标
        target_path = self.get_state("target_path")
        target_type = self.get_state("target_type")

        if not target_path:
            st.info("👈 请先在侧边栏选择一个【文件夹】或【.npy文件】作为输入")
            return

        # 显示选中状态
        st.success(f"当前输入 ({target_type}): `{target_path}`")

        st.divider()

        # 2. 管道配置
        c1, c2, c3 = st.columns(3)
        
        PIPELINE_STEPS = ["step1", "step2", "step3", "step4"]
        PIPELINE_STEP_NAMES = ["1:骨骼归一化", "2:骨骼转换到原点", "3:转换为263维特征向量", "4:将263维特征向量转回22x3"]
        
        with c1:
            start_step = st.selectbox("Start Stage (起点)", PIPELINE_STEP_NAMES, index=0)
        with c2:
            end_step = st.selectbox("End Stage (终点)", PIPELINE_STEP_NAMES, index=2)
        with c3:
            # 简单的逻辑检查
            try:
                s_idx = PIPELINE_STEP_NAMES.index(start_step)
                e_idx = PIPELINE_STEP_NAMES.index(end_step)
                if s_idx > e_idx:
                    st.warning("⚠️ 起点不能晚于终点")
                    valid_config = False
                else:
                    valid_config = True
            except:
                valid_config = True

        start_node = PIPELINE_STEPS[s_idx]
        end_node = PIPELINE_STEPS[e_idx]

        # 3. 输出配置
        default_out = os.path.join(os.path.dirname(target_path), "converted_results")
        output_dir = st.text_input("输出文件夹 (Output Dir)", default_out)

        render_mp4_video = st.toggle(
            "是否渲染mp4视频？（可能会导致速度变慢）", 
            value=False, 
            key="b_render_mp4"
        )
        # 构造命令
        script_path = os.path.join(self.ctx.root_dir, "tool_HumanMLConverter.py")
        if target_type == "dir":
            show_cmd = f"python {script_path} --start_stage {start_node} --end_stage {end_node} --input_dir '{target_path}' --output_dir '{output_dir}'"
        else:
            show_cmd = f"python {script_path} --start_stage {start_node} --end_stage {end_node} --input_file '{target_path}' --output_dir '{output_dir}'"
        
        if render_mp4_video:
            show_cmd += " --render_mp4"
        
        st.code(show_cmd, language="bash")

        # 4. 执行按钮
        if st.button("🚀 开始转换 (Run Pipeline)", type="primary", disabled=not valid_config):
            cmd = show_cmd

            # 运行
            success, msg = ProcessManager.run_with_log(
                command=cmd,
                task_name="motion_convert",
                root_dir=self.ctx.root_dir
            )
            
            if success:
                self.set_state("last_log_path", msg)
                st.success("任务已启动！请查看下方日志。")
                st.rerun() # 刷新以显示日志框
            else:
                st.error(f"启动失败: {msg}")

        # 5. 日志监控
        self.render_log_monitor()
       