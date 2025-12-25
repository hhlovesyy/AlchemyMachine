# # modules/render.py
# import streamlit as st
# import os
# import glob
# import time
# from core.base import BaseModule
# from core.process_mgr import ProcessManager

# class RenderModule(BaseModule):
#     def __init__(self):
#         super().__init__()
#         self.name = "看看你的：渲染"
#         self.icon = "🎬"
        
#         # === ⚠️ 关键路径配置 ===
#         # 原代码中渲染脚本在另一个仓库 MotionLCM 下，这里保持原样
#         self.RENDER_WORK_DIR = "/root/autodl-tmp/MyRepository/MCM-LDM/"
#         self.RENDER_SCRIPT = "render_result.sh"

#     def render_sidebar(self):
#         # st.info("💡 渲染模块运行在 MotionLCM 环境下，但读取的是 MCM-LDM 的结果。")
#         st.caption(f"渲染引擎路径:\n{self.RENDER_WORK_DIR}")

#     def render_main(self):
#         st.markdown("## 🎬 智能渲染工厂")
        
#         # 建立左右分栏 (2:1 比例)
#         col_config, col_preview = st.columns([2, 1])

#         # ================= 左侧：配置区 =================
#         with col_config:
#             st.subheader("1. 数据源配置")
            
#             # 1.1 选择实验大类
#             results_root = os.path.join(self.ctx.root_dir, "results", "mld")
#             if os.path.exists(results_root):
#                 res_dirs = sorted([d for d in os.listdir(results_root) if os.path.isdir(os.path.join(results_root, d))], reverse=True)
#             else:
#                 res_dirs = []

#             if not res_dirs:
#                 st.warning("⚠️ 没有找到生成结果 (results/mld is empty)")
#                 return

#             selected_exp_name = st.selectbox("Step A: 选择实验", res_dirs, key=self._get_key("render_exp"))
#             selected_exp_path = os.path.join(results_root, selected_exp_name)

#             # 1.2 选择具体序列 (Subdir)
#             subdirs = []
#             if os.path.exists(selected_exp_path):
#                 subdirs = [d for d in os.listdir(selected_exp_path) if os.path.isdir(os.path.join(selected_exp_path, d))]
#                 # 按修改时间排序
#                 subdirs = sorted(subdirs, key=lambda x: os.path.getmtime(os.path.join(selected_exp_path, x)), reverse=True)
            
#             if not subdirs:
#                 st.error(f"❌ {selected_exp_name} 下没有子文件夹")
#                 return

#             selected_subdir_name = st.selectbox("Step B: 选择动作序列", subdirs, key=self._get_key("render_subdir"))
#             target_subdir_path = os.path.join(selected_exp_path, selected_subdir_name)
            
#             st.success(f"📂 目标锁定: `.../{selected_subdir_name}`")

#             st.divider()

#             # 1.3 渲染参数
#             st.subheader("2. 渲染参数")
            
#             c1, c2 = st.columns(2)
#             with c1:
#                 render_mode = st.selectbox("模式 (Mode)", ["sequence", "video", "frame"], key=self._get_key("r_mode"))
#                 smplify_iters = st.number_input("SMPL Iters", value=50, key=self._get_key("r_iters"))
            
#             with c2:
#                 # 动态参数逻辑
#                 param_arg = ""
#                 if render_mode == "sequence":
#                     val = st.number_input("帧数 (Frames)", value=4, min_value=1, key=self._get_key("seqence_num"))
#                     param_arg = f"--num {int(val)}"
#                 elif render_mode == "video":
#                     val = st.number_input("帧率 (FPS)", value=20, key=self._get_key("video_fps"))
#                     param_arg = f"--fps {int(val)}"
#                 elif render_mode == "frame":
#                     val = st.slider("帧位置 (0.0-1.0)", 0.0, 1.0, 0.5, key=self._get_key("frame_pos_slider"))
#                     param_arg = f"--exact_frame {val}"

#             c3, c4 = st.columns(2)
#             with c3:
#                 res_quality = st.selectbox("分辨率 (Res)", ["high", "low"], index=0, key=self._get_key("r_res"))
#             with c4:
#                 is_gt = st.checkbox("是 Ground Truth? (绿色)", value=False, key=self._get_key("r_gt"))

#             st.divider()

#             column1, column2 = st.columns(2)
#             with column1:
#                 render_balance = st.checkbox("渲染独木桥？",value=False, key=self._get_key("render_renderBalance"))
#             with column2:
#                 render_lowCeiling = st.checkbox("渲染低矮天花板？", value=False, key=self._get_key("render_renderLowCeiling"))
            
#             # 1.4 执行按钮
#             if st.button("🎨 开始渲染 (Run Pipeline)", type="primary", use_container_width=True, key=self._get_key("run_pipeline")):
#                 self._run_render_pipeline(
#                     target_subdir_path, smplify_iters, render_mode, res_quality, param_arg, is_gt, selected_subdir_name
#                 )

#         # ================= 右侧：预览区 =================
#         with col_preview:
#             st.subheader("📺 结果预览")
#             st.caption(f"正在监视: {selected_subdir_name}")
            
#             if target_subdir_path and os.path.exists(target_subdir_path):
#                 # 扫描 MP4
#                 mp4_files = glob.glob(os.path.join(target_subdir_path, "*.mp4"))
#                 # 按时间倒序，让最新的显示在最上面
#                 mp4_files = sorted(mp4_files, key=os.path.getmtime, reverse=True)
                
#                 if mp4_files:
#                     st.success(f"发现 {len(mp4_files)} 个视频")
#                     for mp4 in mp4_files[:3]: # 只显示前3个
#                         st.video(mp4)
#                         st.caption(os.path.basename(mp4))
                    
#                     if len(mp4_files) > 3:
#                         st.info(f"...还有 {len(mp4_files)-3} 个")
#                 else:
#                     st.warning("暂无视频")
#                     st.caption("请先点击左侧开始渲染，或检查是否只生成了图片")
#             else:
#                 st.error("路径无效")

#         # ================= 下方：日志 =================
#         self.render_log_monitor()

#     def _run_render_pipeline(self, input_path, iters, mode, res, extra_arg, is_gt, session_suffix):
#         # 构造命令
#         # 注意：这里 input_path 可能包含空格，建议用引号包起来，虽然 autodl 路径通常没有空格
#         cmd = f"bash {self.RENDER_SCRIPT} --input_folder '{input_path}' --iters {iters} --mode {mode} --res {res} {extra_arg}"
        
#         if is_gt:
#             cmd += " --gt"

#         # Session Name
#         session_name = f"render_{session_suffix}"[:20]

#         # 提交任务
#         # 注意：这里 root_dir 必须切换到 MotionLCM 的目录
#         success, log_path = ProcessManager.run_with_log(
#             command=cmd,
#             task_name=session_name,
#             root_dir=self.RENDER_WORK_DIR
#         )

#         if success:
#             self.set_state("last_log_path", log_path)
#             st.toast("🎨 渲染任务已启动！")
#             self.set_live2d_state('success')
#             time.sleep(0.5)
#             st.rerun()
#         else:
#             st.error(f"启动失败: {log_path}")


# modules/render.py
import streamlit as st
import os
import glob
import time
from core.base import BaseModule
from core.process_mgr import ProcessManager

class RenderModule(BaseModule):
    def __init__(self):
        super().__init__()
        self.name = "看看你的：渲染"
        self.icon = "🎬"
        
        # === ⚠️ 关键路径配置 ===
        # 原代码中渲染脚本在另一个仓库 MotionLCM 下，这里保持原样
        self.RENDER_WORK_DIR = "/root/autodl-tmp/MyRepository/MCM-LDM/"
        self.RENDER_SCRIPT = "render_result.sh"

    def render_sidebar(self):
        # st.info("💡 渲染模块运行在 MotionLCM 环境下，但读取的是 MCM-LDM 的结果。")
        st.caption(f"渲染引擎路径:\n{self.RENDER_WORK_DIR}")

    def render_main(self):
        st.markdown("## 🎬 智能渲染工厂")
        
        # 建立左右分栏 (2:1 比例)
        col_config, col_preview = st.columns([2, 1])

        # ================= 左侧：配置区 =================
        with col_config:
            st.subheader("1. 数据源配置")
            
            # 1.1 选择实验大类
            results_root = os.path.join(self.ctx.root_dir, "results", "mld")
            if os.path.exists(results_root):
                res_dirs = sorted([d for d in os.listdir(results_root) if os.path.isdir(os.path.join(results_root, d))], reverse=True)
            else:
                res_dirs = []

            if not res_dirs:
                st.warning("⚠️ 没有找到生成结果 (results/mld is empty)")
                return

            selected_exp_name = st.selectbox("Step A: 选择实验", res_dirs, key=self._get_key("render_exp"))
            selected_exp_path = os.path.join(results_root, selected_exp_name)

            # 1.2 选择具体序列 (Subdir)
            subdirs = []
            if os.path.exists(selected_exp_path):
                subdirs = [d for d in os.listdir(selected_exp_path) if os.path.isdir(os.path.join(selected_exp_path, d))]
                # 按修改时间排序
                subdirs = sorted(subdirs, key=lambda x: os.path.getmtime(os.path.join(selected_exp_path, x)), reverse=True)
            
            if not subdirs:
                st.error(f"❌ {selected_exp_name} 下没有子文件夹")
                return

            selected_subdir_name = st.selectbox("Step B: 选择动作序列", subdirs, key=self._get_key("render_subdir"))
            target_subdir_path = os.path.join(selected_exp_path, selected_subdir_name)
            
            st.success(f"📂 目标锁定: `.../{selected_subdir_name}`")

            st.divider()

            # 1.3 渲染参数
            st.subheader("2. 渲染参数")
            
            c1, c2 = st.columns(2)
            with c1:
                render_mode = st.selectbox("模式 (Mode)", ["sequence", "video", "frame"], key=self._get_key("r_mode"))
                smplify_iters = st.number_input("SMPL Iters", value=50, key=self._get_key("r_iters"))
            
            with c2:
                # 动态参数逻辑
                param_arg = ""
                if render_mode == "sequence":
                    val = st.number_input("帧数 (Frames)", value=4, min_value=1, key=self._get_key("seqence_num"))
                    param_arg = f"--num {int(val)}"
                elif render_mode == "video":
                    val = st.number_input("帧率 (FPS)", value=20, key=self._get_key("video_fps"))
                    param_arg = f"--fps {int(val)}"
                elif render_mode == "frame":
                    val = st.slider("帧位置 (0.0-1.0)", 0.0, 1.0, 0.5, key=self._get_key("frame_pos_slider"))
                    param_arg = f"--exact_frame {val}"

            c3, c4 = st.columns(2)
            with c3:
                res_quality = st.selectbox("分辨率 (Res)", ["high", "low"], index=0, key=self._get_key("r_res"))
            with c4:
                is_gt = st.checkbox("是 Ground Truth? (绿色)", value=False, key=self._get_key("r_gt"))

            st.divider()

            column1, column2 = st.columns(2)
            SCENE_NAMES = ["独木桥", "低矮天花板", "暴风雨/雪", "黑暗环境"]
            PIPELINE_SCENES = ["Dumuqiao", "DiAiTianhuaban", "BaoFengYu", "Dark"]
            
            with column1:
                scene_choose = st.selectbox("选择场景",SCENE_NAMES, index=0,  key=self._get_key("render_scene_name"))
            with column2:
                render_hint = st.checkbox("是否渲染用户指引的轨迹？", value=True, key=self._get_key("render_hint"))

            choose_scene_id = SCENE_NAMES.index(scene_choose)
            choose_scene_name = PIPELINE_SCENES[choose_scene_id]

            scene_ctx = {
                "scene_name": choose_scene_name,
                "render_hint": render_hint
            }

            # 1.4 执行按钮
            if st.button("🎨 开始渲染 (Run Pipeline)", type="primary", use_container_width=True, key=self._get_key("run_pipeline")):
                self._run_render_pipeline(
                    target_subdir_path, smplify_iters, render_mode, res_quality, param_arg, is_gt, selected_subdir_name, scene_ctx
                )

        # ================= 右侧：预览区 =================
        with col_preview:
            st.subheader("📺 结果预览")
            st.caption(f"正在监视: {selected_subdir_name}")
            
            if target_subdir_path and os.path.exists(target_subdir_path):
                # 扫描 MP4
                mp4_files = glob.glob(os.path.join(target_subdir_path, "*.mp4"))
                # 按时间倒序，让最新的显示在最上面
                mp4_files = sorted(mp4_files, key=os.path.getmtime, reverse=True)
                
                if mp4_files:
                    st.success(f"发现 {len(mp4_files)} 个视频")
                    for mp4 in mp4_files[:3]: # 只显示前3个
                        st.video(mp4)
                        st.caption(os.path.basename(mp4))
                    
                    if len(mp4_files) > 3:
                        st.info(f"...还有 {len(mp4_files)-3} 个")
                else:
                    st.warning("暂无视频")
                    st.caption("请先点击左侧开始渲染，或检查是否只生成了图片")
            else:
                st.error("路径无效")

        # ================= 下方：日志 =================
        self.render_log_monitor()

    def _run_render_pipeline(self, input_path, iters, mode, res, extra_arg, is_gt, session_suffix, scene_ctx):
        # 构造命令
        # 注意：这里 input_path 可能包含空格，建议用引号包起来，虽然 autodl 路径通常没有空格
        cmd = f"bash {self.RENDER_SCRIPT} --input_folder '{input_path}' --iters {iters} --mode {mode} --res {res} {extra_arg}"
        
        if is_gt:
            cmd += " --gt"
        
        cmd += f" --scene_name {scene_ctx.get('scene_name', 'default_scene')}"
        # st.warning(scene_ctx["render_hint"])
        # st.warning(type(scene_ctx["render_hint"]))
        if scene_ctx["render_hint"] == True:
            cmd += " --use_guide_hint"
        

        # Session Name
        session_name = f"render_{session_suffix}"[:20]

        # 提交任务
        # 注意：这里 root_dir 必须切换到 MotionLCM 的目录
        success, log_path = ProcessManager.run_with_log(
            command=cmd,
            task_name=session_name,
            root_dir=self.RENDER_WORK_DIR
        )

        if success:
            self.set_state("last_log_path", log_path)
            st.toast("🎨 渲染任务已启动！")
            self.set_live2d_state('success')
            time.sleep(0.5)
            st.rerun()
        else:
            st.error(f"启动失败: {log_path}")