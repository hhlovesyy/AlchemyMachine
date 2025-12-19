# modules/training.py
import streamlit as st
import os
import yaml
import copy
import datetime
from core.base import BaseModule
from core.utils import load_yaml, save_yaml, load_persistent_state, save_persistent_state
from core.process_mgr import ProcessManager

class TrainingModule(BaseModule):
    def __init__(self):
        super().__init__()
        self.name = "炼丹模式 (Training)"
        self.icon = "⚗️"
        
        # 路径配置
        self.BASE_YAML_PATH = os.path.join(self.ctx.config_dir, "scenemodiff_train_LiandanBase.yaml")
        self.TRAIN_SCRIPT = os.path.join(self.ctx.root_dir, "train.py")
        
        # 预设配置
        self.PRESETS = {
            "1. Full Model (FiLM+Loss)": {"FUSION": "film", "LOSS": True, "JUST_BASE": False, "LAMBDA": 0.2, "DESC": "完整模型", "SUFFIX": "Full"},
            "2. Only FiLM (No Loss)": {"FUSION": "film", "LOSS": False, "JUST_BASE": False, "LAMBDA": 0.2, "DESC": "无Loss", "SUFFIX": "NoLoss"},
            "3. MLP Fusion (No FiLM)": {"FUSION": "mlp", "LOSS": True, "JUST_BASE": False, "LAMBDA": 0.2, "DESC": "MLP退化", "SUFFIX": "MLP"},
            "4. Only Baseline": {"FUSION": "mlp", "LOSS": False, "JUST_BASE": True, "LAMBDA": 0.0, "DESC": "基线", "SUFFIX": "Base"},
            "5. Custom": {"FUSION": "film", "LOSS": True, "JUST_BASE": False, "LAMBDA": 0.2, "DESC": "自定义", "SUFFIX": "Custom"}
        }

    def render_sidebar(self):
        st.subheader("⚙️ 参数配置")
        
        # === 1. 预设联动回调 ===
        def on_preset_change():
            # 获取当前选择
            k = st.session_state.train_preset
            p = self.PRESETS[k]
            
            # 更新参数
            st.session_state.w_fusion = p["FUSION"]
            st.session_state.w_loss = p["LOSS"]
            st.session_state.w_base = p["JUST_BASE"]
            st.session_state.w_lambda = p["LAMBDA"]
            
            # 🔥 自动生成名字 (带时间戳)
            # 格式: SceneMo_1219_1255_Full
            t_str = datetime.datetime.now().strftime("%m%d_%H%M")
            new_name = f"SceneMo_{t_str}_{p['SUFFIX']}"
            
            # 更新 session_state，这会直接反应到绑定了 key='w_exp_name' 的输入框上
            st.session_state.w_exp_name = new_name

        # 预设选择
        keys = list(self.PRESETS.keys())
        st.radio("预设模板", keys, key="train_preset", on_change=on_preset_change)
        
        st.divider()
        
        # 初始化 Session State (如果还没初始化)
        if 'w_exp_name' not in st.session_state:
            t_str = datetime.datetime.now().strftime("%m%d_%H%M")
            st.session_state.w_fusion = "film"
            st.session_state.w_loss = True
            st.session_state.w_base = False
            st.session_state.w_lambda = 0.2
            st.session_state.w_exp_name = f"SceneMo_{t_str}_Full"

        # 详细参数
        self.fusion = st.selectbox("Fusion Mode", ["film", "mlp"], key="w_fusion")
        self.loss = st.checkbox("Use Scene Loss", key="w_loss")
        self.base = st.checkbox("Just Baseline", key="w_base")
        self.lam = st.number_input("Lambda", 0.0, 10.0, 0.2, step=0.1, key="w_lambda")
        
        st.divider()
        self.lr = st.text_input("LR", load_persistent_state("last_lr", "2e-5"))
        self.bs = st.number_input("Batch Size", 1, 128, 32)
        self.epoch = st.number_input("Epochs", 1, 1000, 100)
        
        # 🔥 关键：绑定 key="w_exp_name"
        # 这样 on_preset_change 修改 session_state.w_exp_name 时，这里会自动更新显示
        self.exp_name = st.text_input("Exp Name", key="w_exp_name")

    def render_main(self):
        st.markdown("## ⚗️ 炼丹控制台")
        
        if not os.path.exists(self.BASE_YAML_PATH):
            st.error(f"❌ 找不到 Base YAML: {self.BASE_YAML_PATH}")
            return
            
        # === 1. 准备配置 ===
        cfg = load_yaml(self.BASE_YAML_PATH)
        new_cfg = copy.deepcopy(cfg)
        
        new_cfg['NAME'] = self.exp_name
        new_cfg.setdefault('SCENE_MODIFF_ABLATION', {})
        new_cfg['SCENE_MODIFF_ABLATION'].update({
            'FUSION_MODE': self.fusion,
            'USE_SCENE_CLS': self.loss,
            'LAMBDA_SCENE': self.lam,
            'JUST_FINETUNE_BASELINE': self.base
        })
        new_cfg['TRAIN']['BATCH_SIZE'] = int(self.bs)
        new_cfg['TRAIN']['END_EPOCH'] = int(self.epoch)
        new_cfg['TRAIN']['OPTIM']['LR'] = float(self.lr)

        # 路径计算
        exp_dir = os.path.join(self.ctx.root_dir, "experiments", "mld", self.exp_name)
        target_yaml_path = os.path.join(exp_dir, "launcher_config.yaml")
        ckpt_dir = os.path.join(exp_dir, "checkpoints")

        # === 2. 信息展示区 (你要的路径提示) ===
        st.info(f"📂 **配置文件**: `{target_yaml_path}`")
        st.success(f"💾 **结果/权重 (Checkpoints) 将保存在**: \n`{ckpt_dir}`")

        # === 3. YAML 预览 ===
        with st.expander("👀 预览生成的 YAML 内容"):
            st.code(yaml.dump(new_cfg, default_flow_style=False), language='yaml')

        # === 4. 启动按钮 ===
        if st.button("🚀 立即启动 (Run)", type="primary", use_container_width=True):
            self._run(new_cfg, exp_dir, target_yaml_path)

        # === 5. 日志监控 ===
        self.render_log_monitor()

    def _run(self, cfg_data, exp_dir, yaml_path):
        os.makedirs(exp_dir, exist_ok=True)
        save_yaml(cfg_data, yaml_path)
        save_persistent_state("last_lr", self.lr)
        
        # 构造真实命令
        cmd = (
            f"python -u {self.TRAIN_SCRIPT} "
            f"--cfg {yaml_path} "
            f"--cfg_assets {self.ctx.assets_file} "
            f"--batch_size {self.bs} "
            f"--nodebug"
        )
        
        screen_id = f"train_{self.exp_name}"[:30]
        
        # 执行
        success, log = ProcessManager.run_with_log(cmd, screen_id, self.ctx.root_dir)
        
        if success:
            self.set_state("last_log_path", log)
            
            # 显示 VSCode 连接提示
            st.markdown("### 🔍 VSCode 监控指令")
            st.code(f"screen -D -r {screen_id}", language="bash")
            st.caption("👆 复制上面这行命令到 VSCode 终端，即可看到带进度条的实时界面！")
            
            st.toast("任务启动成功！")
            import time
            time.sleep(0.5)
            st.rerun()
        else:
            st.error(f"启动失败: {log}")