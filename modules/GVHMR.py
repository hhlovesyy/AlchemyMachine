# # modules/gvhmr_module.py
# import streamlit as st
# import os
# import time
# import shutil
# from core.base import BaseModule
# from core.process_mgr import ProcessManager

# class GVHMRRunner(BaseModule):
#     def render_sidebar(self):
#         st.header("💃 GVHMR 动作提取")
        
#         # === 路径配置 ===
#         self.gvhmr_root = st.text_input(
#             "GVHMR 项目根路径", 
#             value="/root/autodl-tmp/GVHMR"
#         )
        
#         self.input_folder_name = st.text_input(
#             "输入文件夹 (相对路径)", 
#             value="inputs/demo/my_batch_input"
#         )
        
#         self.output_folder_name = st.text_input(
#             "输出文件夹 (相对路径)", 
#             value="outputs/demo/my_batch_output"
#         )

#         self.smpl_path = st.text_input(
#             "SMPL 模型路径",
#             value="/root/autodl-tmp/GVHMR/inputs/checkpoints/body_models/smpl"
#         )
        
#         self.gpu_id = st.text_input("GPU ID", "0")
#         self.skip_visual_odometry = st.checkbox("跳过视觉里程计 (-s)", value=True, help="如果相机是静止的，勾选此项速度更快")

#     def render_main(self):
#         # 拼接完整路径
#         input_dir = os.path.join(self.gvhmr_root, self.input_folder_name)
#         output_dir = os.path.join(self.gvhmr_root, self.output_folder_name)
        
#         # 确保输入目录存在
#         if not os.path.exists(input_dir):
#             os.makedirs(input_dir, exist_ok=True)
            
#         st.info(f"📂 视频存放目录: `{input_dir}`")
#         st.info(f"📂 结果输出目录: `{output_dir}`")
        
#         st.divider()

#         # ==================== 1. 批量上传视频 ====================
#         st.subheader("1. 批量上传视频")
#         uploaded_files = st.file_uploader("选择MP4视频文件", type=['mp4', 'mov', 'avi'], accept_multiple_files=True)
        
#         if uploaded_files:
#             if st.button(f"📥 保存 {len(uploaded_files)} 个视频到服务器"):
#                 progress_bar = st.progress(0)
#                 for idx, uploaded_file in enumerate(uploaded_files):
#                     file_path = os.path.join(input_dir, uploaded_file.name)
#                     with open(file_path, "wb") as f:
#                         f.write(uploaded_file.getbuffer())
#                     progress_bar.progress((idx + 1) / len(uploaded_files))
#                 st.success("✅ 视频上传完成！")

#         # 显示当前目录下的视频列表
#         current_videos = [f for f in os.listdir(input_dir) if f.endswith(('.mp4', '.mov', '.avi'))]
#         with st.expander(f"查看当前待处理视频 ({len(current_videos)}个)"):
#             st.write(current_videos)

#         st.divider()

#         # ==================== 2. 运行 GVHMR 推理 ====================
#         st.subheader("2. 运行 GVHMR 推理")
        
#         # 构造推理命令
#         # python tools/demo/demo_folder.py -f inputs/... -d outputs/... -s
#         flag_s = "-s" if self.skip_visual_odometry else ""
#         # inference_cmd = (
#         #     f"CUDA_VISIBLE_DEVICES={self.gpu_id} "
#         #     f"python tools/demo/demo_folder.py "
#         #     f"-f {self.input_folder_name} "
#         #     f"-d {self.output_folder_name} "
#         #     f"{flag_s}"
#         # )
#         # ==================== 修复点 ====================
#         # 加上 PYTHONPATH=. 告诉 python 在当前目录下寻找 hmr4d 模块
#         inference_cmd = (
#             f"CUDA_VISIBLE_DEVICES={self.gpu_id} "
#             f"PYTHONPATH=. " 
#             f"python tools/demo/demo_folder.py "
#             f"-f {self.input_folder_name} "
#             f"-d {self.output_folder_name} "
#             f"{flag_s}"
#         )
#         # ===============================================
        
#         st.code(f"cd {self.gvhmr_root}\n{inference_cmd}", language="bash")
        
#         if st.button("🚀 开始批量推理 (GVHMR)", type="primary"):
#             task_name = "gvhmr_inference"
#             success, msg = ProcessManager.run_with_log(
#                 command=inference_cmd,
#                 task_name=task_name,
#                 root_dir=self.gvhmr_root
#             )
#             if success:
#                 st.toast(f"GVHMR 推理已后台启动: {task_name}")
#                 self.set_state("last_log_path", msg) # 联动日志监控
#                 time.sleep(1)
#                 st.rerun()
#             else:
#                 st.error(f"启动失败: {msg}")

#         st.divider()

#         # ==================== 3. 批量转换为 NPY ====================
#         st.subheader("3. 结果转换为 NPY")
#         st.markdown("该步骤会自动扫描输出文件夹，将 `.pt` 转换为 MLD 可用的 `motion_22joints.npy`。")
        
#         # 构造转换命令
#         # python tools/batch_convert.py --root_dir ... --smpl_dir ...
#         convert_cmd = (
#             f"python tools/MY_convertTool/batch_convert_pt2npy.py " # /root/autodl-tmp/GVHMR/tools/MY_convertTool/batch_convert_pt2npy.py
#             f"--root_dir {output_dir} "
#             f"--smpl_dir {self.smpl_path}"
#         )
        
#         st.code(f"cd {self.gvhmr_root}\n{convert_cmd}", language="bash")
        
#         if st.button("🔄 开始批量转换 (PT -> NPY)"):
#             task_name = "gvhmr_convert"
#             success, msg = ProcessManager.run_with_log(
#                 command=convert_cmd,
#                 task_name=task_name,
#                 root_dir=self.gvhmr_root
#             )
#             if success:
#                 st.toast(f"转换任务已后台启动: {task_name}")
#                 self.set_state("last_log_path", msg)
#                 time.sleep(1)
#                 st.rerun()
#             else:
#                 st.error(f"启动失败: {msg}")

#         # 日志监控组件 (复用你原本的逻辑)
#         self.render_log_monitor()


# modules/gvhmr_module.py
import streamlit as st
import os
import time
from datetime import datetime
from core.base import BaseModule
from core.process_mgr import ProcessManager

class GVHMRRunner(BaseModule):
    def render_sidebar(self):
        st.header("💃 GVHMR 动作提取")
        
        # === 基础配置 ===
        self.gvhmr_root = st.text_input(
            "GVHMR 项目根路径", 
            value="/root/autodl-tmp/GVHMR"
        )
        
        # SMPL 模型路径
        self.smpl_path = st.text_input(
            "SMPL 模型路径",
            value="/root/autodl-tmp/GVHMR/inputs/checkpoints/body_models/smpl"
        )
        
        # 显卡和参数
        col1, col2 = st.columns(2)
        with col1:
            self.gpu_id = st.text_input("GPU ID", "0")
        with col2:
            self.skip_visual_odometry = st.checkbox("跳过视觉里程计 (-s)", value=True)

    def render_main(self):
        # 定义基础目录
        base_input_dir = os.path.join(self.gvhmr_root, "inputs/demo")
        base_output_dir = os.path.join(self.gvhmr_root, "outputs/demo")
        
        # 确保基础目录存在
        os.makedirs(base_input_dir, exist_ok=True)
        os.makedirs(base_output_dir, exist_ok=True)

        st.info("💡 流程：新建批次 -> 上传视频 -> 选择该批次 -> 运行推理 -> 转换数据")
        st.divider()

        # ==================== 1. 新建批次与上传 ====================
        st.subheader("1. 上传视频 (新建批次)")
        
        # A. 自动生成带时间戳的文件夹名
        default_batch_name = datetime.now().strftime("batch_%Y%m%d_%H%M%S")
        
        # B. 允许用户修改名字
        new_batch_name = st.text_input("📁 设置新批次文件夹名称", value=default_batch_name)
        
        uploaded_files = st.file_uploader("选择视频文件 (支持批量)", type=['mp4', 'mov', 'avi'], accept_multiple_files=True)
        
        if uploaded_files:
            target_folder = os.path.join(base_input_dir, new_batch_name)
            
            if st.button(f"📥 确认上传 {len(uploaded_files)} 个视频"):
                # 创建文件夹
                os.makedirs(target_folder, exist_ok=True)
                
                # 保存文件
                progress_bar = st.progress(0)
                for idx, uploaded_file in enumerate(uploaded_files):
                    file_path = os.path.join(target_folder, uploaded_file.name)
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    progress_bar.progress((idx + 1) / len(uploaded_files))
                
                st.success(f"✅ 上传完成！已存入: {new_batch_name}")
                # 记录状态，以便刷新后下拉框能默认选中这个新文件夹
                self.set_state("last_uploaded_batch", new_batch_name)
                time.sleep(1)
                st.rerun()

        st.divider()

        # ==================== 2. 选择批次并推理 ====================
        st.subheader("2. 运行 GVHMR 推理")

        # C. 扫描现有文件夹，做成下拉菜单
        # 获取 base_input_dir 下的所有子文件夹
        try:
            all_batches = [d for d in os.listdir(base_input_dir) if os.path.isdir(os.path.join(base_input_dir, d))]
            all_batches.sort(reverse=True) # 让最新的排前面
        except FileNotFoundError:
            all_batches = []

        # 获取上次上传的文件夹名作为默认值
        default_idx = 0
        last_batch = self.get_state("last_uploaded_batch")
        if last_batch and last_batch in all_batches:
            default_idx = all_batches.index(last_batch)

        # 下拉选择框
        selected_batch = st.selectbox("📂 选择要处理的输入文件夹", all_batches, index=default_idx)

        if not selected_batch:
            st.warning("⚠️ 暂无输入文件夹，请先上传视频。")
            return

        # D. 自动映射输出路径 (输入叫什么，输出就叫什么)
        input_rel_path = f"inputs/demo/{selected_batch}"
        output_rel_path = f"outputs/demo/{selected_batch}"
        
        full_output_path = os.path.join(self.gvhmr_root, output_rel_path)

        # 显示映射关系
        col_in, col_arrow, col_out = st.columns([4, 1, 4])
        with col_in:
            st.text_input("输入路径 (自动)", value=input_rel_path, disabled=True)
        with col_arrow:
            st.markdown("<h3 style='text-align: center;'>➡️</h3>", unsafe_allow_html=True)
        with col_out:
            st.text_input("输出路径 (自动)", value=output_rel_path, disabled=True)

        # 构造推理命令
        flag_s = "-s" if self.skip_visual_odometry else ""
        
        # 指定 GVHMR 环境 python (请根据实际情况修改路径)
        python_exec = "/root/miniconda3/envs/gvhmr/bin/python"
        
        inference_cmd = (
            f"CUDA_VISIBLE_DEVICES={self.gpu_id} "
            f"PYTHONPATH=. "
            f"{python_exec} tools/demo/demo_folder.py "
            f"-f {input_rel_path} "
            f"-d {output_rel_path} "
            f"{flag_s}"
        )
        
        # 这里的 key=inference_cmd 确保命令变了按钮状态也会重置
        if st.button("🚀 开始批量推理 (GVHMR)", type="primary", key="btn_infer"):
            task_name = f"gvhmr_{selected_batch}"
            success, msg = ProcessManager.run_with_log(
                command=inference_cmd,
                task_name=task_name,
                root_dir=self.gvhmr_root
            )
            if success:
                st.toast(f"GVHMR 推理已启动: {task_name}")
                self.set_state("last_log_path", msg)
                time.sleep(1)
                st.rerun()
            else:
                st.error(f"启动失败: {msg}")

        st.divider()

        # ==================== 3. 批量转换为 NPY ====================
        st.subheader("3. 结果转换为 NPY")
        st.markdown(f"将 **`{output_rel_path}`** 下的所有结果转换为以视频命名的 `.npy` 文件。")
        
        convert_cmd = (
            f"{python_exec} tools/MY_convertTool/batch_convert_pt2npy.py "
            f"--root_dir {full_output_path} "
            f"--smpl_dir {self.smpl_path}"
        )
        
        if st.button("🔄 开始批量转换 (PT -> NPY)", key="btn_convert"):
            task_name = f"convert_{selected_batch}"
            success, msg = ProcessManager.run_with_log(
                command=convert_cmd,
                task_name=task_name,
                root_dir=self.gvhmr_root
            )
            if success:
                st.toast(f"转换任务已启动: {task_name}")
                self.set_state("last_log_path", msg)
                time.sleep(1)
                st.rerun()
            else:
                st.error(f"启动失败: {msg}")

        # 日志监控
        self.render_log_monitor()