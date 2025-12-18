# # modules/training.py
# import streamlit as st
# from core.base import BaseModule

# class TrainingModule(BaseModule):
#     # __init__ 里不需要设 name 了，全靠 yaml 配置
    
#     def render_sidebar(self):
#         # 注意：这里不需要写 st.sidebar.xxx
#         # 因为基类已经把它包在 with st.sidebar: 里了
#         st.info("这里是侧边栏配置区")
#         self.batch_size = st.number_input("Batch Size", 32)
#         self.lr = st.text_input("Learning Rate", "1e-4")
#         if st.button("更新配置"):
#             st.toast("配置已更新")

#     def render_main(self):
#         st.success(f"当前 Batch Size: {getattr(self, 'batch_size', 32)}")
#         st.write("这里是主工作区，可以放监控图表、日志输出等...")
        
#         col1, col2 = st.columns(2)
#         with col1:
#             st.metric("显存占用", "12GB", "+1.2GB")
#         with col2:
#             if st.button("开始炼丹", type="primary"):
#                 st.write("启动进程中...")



# modules/training.py
import streamlit as st
import os
import yaml
import copy
import datetime
import subprocess
from core.base import BaseModule
from core.utils import load_yaml, save_yaml, load_persistent_state, save_persistent_state
from core.process_mgr import ProcessManager

class TrainingModule(BaseModule):
    def __init__(self):
        super().__init__()
        self.name = "炼丹模式 (Training)"
        self.icon = "⚗️"

        # === 核心路径配置 ===
        self.BASE_YAML_PATH = os.path.join(self.ctx.config_dir, "scenemodiff_train_LiandanBase.yaml")
        self.TRAIN_SCRIPT = os.path.join(self.ctx.root_dir, "train.py")
        
        # === 预设配置库 (原版复刻) ===
        self.PRESETS = {
            "1. Full Model (FiLM+Loss)": {
                "FUSION": "film", "LOSS": True, "JUST_BASE": False, "LAMBDA": 0.2, 
                "DESC": "完整模型：FiLM融合 + 场景一致性Loss",
                "SUFFIX": "Full_FiLM_Loss"
            },
            "2. Only FiLM (No Loss)": {
                "FUSION": "film", "LOSS": False, "JUST_BASE": False, "LAMBDA": 0.2, 
                "DESC": "验证Loss作用：保留FiLM，关掉Loss",
                "SUFFIX": "FiLM_NoLoss"
            },
            "3. MLP Fusion (No FiLM)": {
                "FUSION": "mlp", "LOSS": True, "JUST_BASE": False, "LAMBDA": 0.2, 
                "DESC": "验证FiLM作用：退化为MLP融合，保留Loss",
                "SUFFIX": "MLP_WithLoss"
            },
            "4. Only Baseline": {
                "FUSION": "mlp", "LOSS": False, "JUST_BASE": True, "LAMBDA": 0.0, 
                "DESC": "纯基线：无FiLM，无Loss，无模块",
                "SUFFIX": "BaselineOnly"
            },
            "5. Custom (自定义)": {
                "FUSION": "film", "LOSS": True, "JUST_BASE": False, "LAMBDA": 0.2, 
                "DESC": "自由调整参数，不使用预设模板",
                "SUFFIX": "Custom"
            }
        }

    def render_sidebar(self):
        st.subheader("⚗️ 炼丹配置室")
        
        # === 1. 预设选择器 (带回调) ===
        def on_preset_change():
            """当预设改变时，自动刷新下方的 Session State"""
            selection = st.session_state.train_preset_selector
            cfg = self.PRESETS[selection]
            
            # 更新控件绑定的 State
            st.session_state.w_fusion = cfg["FUSION"]
            st.session_state.w_loss = cfg["LOSS"]
            st.session_state.w_base = cfg["JUST_BASE"]
            st.session_state.w_lambda = float(cfg["LAMBDA"])
            
            # 更新实验名
            time_str = datetime.datetime.now().strftime("%m%d_%H%M")
            st.session_state.w_exp_name = f"SceneMo_{time_str}_{cfg['SUFFIX']}"

        # 预设 Radio
        preset_options = list(self.PRESETS.keys())
        st.radio(
            "⚡ 快速选择实验配置:",
            options=preset_options,
            key="train_preset_selector",
            on_change=on_preset_change,
            index=0
        )
        
        # 显示当前预设说明
        current_preset = self.PRESETS[st.session_state.get("train_preset_selector", preset_options[0])]
        st.info(f"💡 说明: {current_preset['DESC']}")
        
        st.divider()

        # === 2. 参数编辑区 (绑定 Session State) ===
        # 初始化默认值 (防止第一次运行报错)
        if 'w_fusion' not in st.session_state:
            init_cfg = self.PRESETS[preset_options[0]]
            st.session_state.w_fusion = init_cfg["FUSION"]
            st.session_state.w_loss = init_cfg["LOSS"]
            st.session_state.w_base = init_cfg["JUST_BASE"]
            st.session_state.w_lambda = init_cfg["LAMBDA"]
            st.session_state.w_exp_name = f"SceneMo_{datetime.datetime.now().strftime('%m%d_%H%M')}_{init_cfg['SUFFIX']}"

        st.markdown("#### 核心超参")
        self.fusion_mode = st.selectbox("FUSION_MODE", ["film", "mlp"], key="w_fusion")
        self.use_loss = st.checkbox("USE_SCENE_CLS", key="w_loss")
        self.just_base = st.checkbox("JUST_FINETUNE_BASELINE", key="w_base")
        self.lambda_scene = st.number_input("LAMBDA_SCENE", format="%.2f", step=0.1, key="w_lambda")

        st.markdown("#### 训练设置")
        # 读取持久化的上次 LR
        last_lr = load_persistent_state("last_lr", "2e-5")
        
        self.lr = st.text_input("Learning Rate", value=last_lr)
        self.batch_size = st.number_input("Batch Size", value=32)
        self.end_epoch = st.number_input("End Epoch", value=100)
        self.exp_name = st.text_input("Experiment NAME", key="w_exp_name")

        st.divider()
        
        # === 3. 进程查看器 (Sidebar版) ===
        st.subheader("Process Monitor")
        if st.checkbox("显示 Python 进程", value=False):
            try:
                # 简单实现 grep
                cmd = "ps -ef | grep python | grep -v grep | grep -E 'train.py|demo|render'"
                output = subprocess.check_output(cmd, shell=True).decode("utf-8")
                st.code(output if output else "无相关进程", language="bash")
            except:
                st.warning("查询进程失败")


    def render_main(self):
        st.markdown("## ⚗️ 智能炼丹控制台")
        
        # 检查 Base YAML
        if not os.path.exists(self.BASE_YAML_PATH):
            st.error(f"❌ 找不到基准配置文件: `{self.BASE_YAML_PATH}`\n请确保 configs 目录下有该文件！")
            return

        # 1. 读取并修改配置
        base_config = load_yaml(self.BASE_YAML_PATH)
        new_config = copy.deepcopy(base_config) # 关键：防止污染

        # 修改配置字典
        new_config['NAME'] = self.exp_name
        
        # 确保 Key 存在
        if 'SCENE_MODIFF_ABLATION' not in new_config: new_config['SCENE_MODIFF_ABLATION'] = {}
        if 'TRAIN' not in new_config: new_config['TRAIN'] = {}
        if 'OPTIM' not in new_config['TRAIN']: new_config['TRAIN']['OPTIM'] = {}

        # 注入参数
        new_config['SCENE_MODIFF_ABLATION']['FUSION_MODE'] = self.fusion_mode
        new_config['SCENE_MODIFF_ABLATION']['USE_SCENE_CLS'] = self.use_loss
        new_config['SCENE_MODIFF_ABLATION']['LAMBDA_SCENE'] = self.lambda_scene
        new_config['SCENE_MODIFF_ABLATION']['JUST_FINETUNE_BASELINE'] = self.just_base
        
        new_config['TRAIN']['BATCH_SIZE'] = int(self.batch_size)
        new_config['TRAIN']['END_EPOCH'] = int(self.end_epoch)
        new_config['TRAIN']['OPTIM']['LR'] = float(self.lr)

        # 2. 预览区域
        with st.expander("👀 预览生成的 YAML 配置 (点击展开)", expanded=False):
            st.code(yaml.dump(new_config, default_flow_style=False), language='yaml')

        # 3. 启动按钮区域
        col_btn, col_info = st.columns([1, 3])
        with col_btn:
            start_btn = st.button("🚀 开始炼丹 (Start)", type="primary", use_container_width=True)
        
        with col_info:
            if start_btn:
                self._start_training(new_config)

        # 4. 日志监控组件
        self.render_log_monitor()

    def _start_training(self, config_data):
        # A. 创建目录
        exp_dir = os.path.join(self.ctx.root_dir, "experiments", "mld", self.exp_name)
        try:
            os.makedirs(exp_dir, exist_ok=True)
        except Exception as e:
            st.error(f"❌ 创建目录失败: {e}")
            return

        # B. 保存 YAML
        new_yaml_path = os.path.join(exp_dir, "launcher_config.yaml")
        save_yaml(config_data, new_yaml_path)
        
        # 保存用户习惯 (LR)
        save_persistent_state("last_lr", self.lr)
        
        st.toast(f"配置已保存: {os.path.basename(new_yaml_path)}")
        
        # C. 构造命令
        # 注意：这里使用了 --nodebug 来减少控制台垃圾输出，配合日志文件更好
        cmd = (
            f"python -u {self.TRAIN_SCRIPT} "
            f"--cfg {new_yaml_path} "
            f"--cfg_assets {self.ctx.assets_file} "
            f"--batch_size {self.batch_size} "
            f"--nodebug"
        )
        
        screen_name = f"train_{self.exp_name}"[:25]
        
        # D. 后台运行
        success, log_path = ProcessManager.run_with_log(
            command=cmd,
            task_name=screen_name,
            root_dir=self.ctx.root_dir
        )
        
        if success:
            self.set_state("last_log_path", log_path)
            st.balloons()
            st.success(f"🎉 训练任务已启动！Session: `{screen_name}`")
            
            # 自动刷新显示日志
            import time
            time.sleep(1)
            st.rerun()
        else:
            st.error(f"启动失败: {log_path}")