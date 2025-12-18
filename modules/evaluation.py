# modules/evaluation.py
import streamlit as st
import os
import glob
import re
import time
from core.base import BaseModule
from core.utils import load_yaml, save_yaml
from core.process_mgr import ProcessManager

class EvaluationModule(BaseModule):
    def __init__(self):
        super().__init__()
        self.name = "评估模式 (Eval)"
        self.icon = "📊"

    def render_sidebar(self):
        st.subheader("📊 评估资源配置")
        st.info("💡 评估分为两阶段：先生成 Motion (Stage 1)，再计算一致性 (Stage 2)。")
        
        # ================= Stage 0: 基础设置 (用于 Stage 1) =================
        st.markdown("#### 1. 待评估模型 (For Stage 1)")
        
        exp_root = os.path.join(self.ctx.root_dir, "experiments", "mld")
        if os.path.exists(exp_root):
            exps = sorted(os.listdir(exp_root), key=lambda x: os.path.getmtime(os.path.join(exp_root, x)), reverse=True)
        else:
            exps = []

        if not exps:
            st.error("⚠️ 未找到实验记录")
            return

        # 选择实验
        self.selected_exp_name = st.selectbox("选择实验", exps, key="eval_exp_sb")
        self.exp_path = os.path.join(exp_root, self.selected_exp_name)

        # 选择 Checkpoint
        ckpt_dir = os.path.join(self.exp_path, "checkpoints")
        ckpt_names = []
        if os.path.exists(ckpt_dir):
            ckpts = glob.glob(os.path.join(ckpt_dir, "*.ckpt"))
            ckpt_names = [os.path.basename(c) for c in ckpts]
            # 简单按长度排序（原版逻辑），你也可以改回正则排序
            ckpt_names = sorted(ckpt_names, key=lambda x: len(x), reverse=True) 
        
        self.selected_ckpt_name = st.selectbox("选择 Checkpoint", ckpt_names, key="eval_ckpt_sb")
        self.selected_ckpt_path = os.path.join(ckpt_dir, self.selected_ckpt_name) if self.selected_ckpt_name else None

    def render_main(self):
        st.markdown("## 📊 智能评估中心 (Two-Stage)")
        
        if not hasattr(self, 'selected_ckpt_path') or not self.selected_ckpt_path:
            st.warning("👈 请先在侧边栏选择要评估的模型！")
            return

        # ================= Stage 1: Standard Evaluation =================
        st.markdown("### 1️⃣ Stage 1: 生成与标准指标")
        st.markdown("> 运行 `run_evaluation.sh`，生成 Motion PKL 文件并计算 FID/Run/Div 等指标。")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.caption(f"Target Exp: `{self.selected_exp_name}`")
            st.caption(f"Target Ckpt: `{self.selected_ckpt_name}`")
        with col2:
            btn_s1 = st.button("🚀 运行 Stage 1", type="primary", use_container_width=True)

        if btn_s1:
            self._run_stage_1()

        st.divider()

        # ================= Stage 2: SCA Evaluation =================
        st.markdown("### 2️⃣ Stage 2: 语义一致性 (SCA)")
        st.markdown("> 运行 `evaluate_sca.py`，需要 Stage 1 生成的 PKL 文件。")

        # --- Stage 2 的选择逻辑放主界面，因为它依赖结果 ---
        results_root = os.path.join(self.ctx.root_dir, "results", "mld")
        
        # 扫描结果目录
        if os.path.exists(results_root):
            res_dirs = sorted([d for d in os.listdir(results_root) if os.path.isdir(os.path.join(results_root, d))], reverse=True)
        else:
            res_dirs = []
        
        c2_1, c2_2 = st.columns([1, 2])
        with c2_1:
            # 默认尝试选中和当前 experiment 名字相似的文件夹
            default_idx = 0
            # 尝试智能匹配：如果 Stage 1 生成了 xxx_Eval，这里自动选中
            target_guess = f"{self.selected_exp_name}_Eval"
            if target_guess in res_dirs:
                default_idx = res_dirs.index(target_guess)
            
            target_res_dir = st.selectbox("选择结果文件夹", res_dirs, index=default_idx, key="sca_dir_select")
        
        pkl_files = []
        if target_res_dir:
            full_res_path = os.path.join(results_root, target_res_dir)
            pkl_files = glob.glob(os.path.join(full_res_path, "crafmd*.pkl"))
            pkl_files = [os.path.basename(p) for p in pkl_files]
            
        with c2_2:
            if pkl_files:
                target_pkl_name = st.selectbox("选择 PKL 文件", pkl_files, key="sca_pkl_select")
                full_pkl_path = os.path.join(full_res_path, target_pkl_name)
            else:
                st.warning("⚠️ 该文件夹下没找到 crafmd*.pkl 文件 (可能是Stage 1还没跑完)")
                target_pkl_name = None
                full_pkl_path = None

        # 运行按钮
        if st.button("🚀 运行 Stage 2 (SCA)", disabled=(not full_pkl_path)):
            self._run_stage_2(full_pkl_path)

        # ================= 日志监控 =================
        self.render_log_monitor()

    # ================= 核心逻辑：Stage 1 =================
    def _run_stage_1(self):
        # 1. 准备配置
        launcher_yaml = os.path.join(self.exp_path, "launcher_config.yaml")
        if not os.path.exists(launcher_yaml):
            # 兜底
            yamls = glob.glob(os.path.join(self.exp_path, "*.yaml"))
            launcher_yaml = yamls[0] if yamls else None
        
        if not launcher_yaml:
            st.error("❌ 找不到 yaml 配置文件")
            return

        eval_cfg = load_yaml(launcher_yaml)
        if 'TEST' not in eval_cfg: eval_cfg['TEST'] = {}
        eval_cfg['TEST']['CHECKPOINTS'] = self.selected_ckpt_path
        
        # 保存临时配置
        temp_eval_yaml_path = os.path.join(self.ctx.config_dir, f"eval_temp_{self.selected_exp_name}.yaml")
        save_yaml(eval_cfg, temp_eval_yaml_path)
        
        # 2. 注入 run_evaluation.sh
        target_exp_name = f"{self.selected_exp_name}_Eval"
        bash_script_path = os.path.join(self.ctx.root_dir, "run_evaluation.sh")
        
        try:
            with open(bash_script_path, 'r', encoding='utf-8') as f:
                bash_content = f.read()
            
            # 正则替换 CONFIG_MLD="..."
            bash_content = re.sub(r'CONFIG_MLD=".*?"', f'CONFIG_MLD="{temp_eval_yaml_path}"', bash_content)
            # 正则替换 EXP_NAME="..."
            bash_content = re.sub(r'EXP_NAME=".*?"', f'EXP_NAME="{target_exp_name}"', bash_content)
            
            with open(bash_script_path, 'w', encoding='utf-8') as f:
                f.write(bash_content)
            
            st.toast(f"✅ Bash注入成功: Target={target_exp_name}")
        except Exception as e:
            st.error(f"❌ 修改 Bash 脚本失败: {e}")
            return

        # 3. 运行
        # 结果将生成在 stage1_eval.log
        cmd = f"bash run_evaluation.sh"
        session_name = "stage1_eval"
        
        success, log_path = ProcessManager.run_with_log(cmd, session_name, self.ctx.root_dir)
        
        if success:
            self.set_state("last_log_path", log_path)
            st.toast("Stage 1 任务已启动！")
            time.sleep(0.5)
            st.rerun()

    # ================= 核心逻辑：Stage 2 =================
    def _run_stage_2(self, pkl_path):
        # 1. 注入 evaluate_sca.py (Python Injection)
        sca_script_path = os.path.join(self.ctx.root_dir, "evaluate_sca.py")
        try:
            with open(sca_script_path, 'r', encoding='utf-8') as f:
                py_content = f.read()
            
            # 替换 input_path = "..."
            new_line = f'input_path = "{pkl_path}"'
            py_content = re.sub(r'input_path\s*=\s*".*?"', new_line, py_content)
            
            with open(sca_script_path, 'w', encoding='utf-8') as f:
                f.write(py_content)
            st.toast(f"✅ Python注入成功: Input={os.path.basename(pkl_path)}")
        except Exception as e:
            st.error(f"❌ 修改 Python 脚本失败: {e}")
            return

        # 2. 注入 run_evaluation_sca.sh (Bash Injection)
        # 需要找到 yaml 配置，这里我们复用 Stage 1 选中的实验的配置
        # 因为 SCA 评估也需要加载模型结构配置
        launcher_yaml = os.path.join(self.exp_path, "launcher_config.yaml")
        if not os.path.exists(launcher_yaml):
            yamls = glob.glob(os.path.join(self.exp_path, "*.yaml"))
            launcher_yaml = yamls[0] if yamls else ""
            
        if not launcher_yaml:
            st.error("❌ 找不到对应的 yaml 配置文件，无法运行 Stage 2")
            return

        sca_bash_path = os.path.join(self.ctx.root_dir, "run_evaluation_sca.sh")
        try:
            with open(sca_bash_path, 'r', encoding='utf-8') as f:
                bash_content = f.read()
            
            # 替换 CONFIG_FILE="..."
            bash_content = re.sub(r'CONFIG_FILE=".*?"', f'CONFIG_FILE="{launcher_yaml}"', bash_content)
            
            with open(sca_bash_path, 'w', encoding='utf-8') as f:
                f.write(bash_content)
            st.toast(f"✅ Bash注入成功: Config={os.path.basename(launcher_yaml)}")
        except Exception as e:
            st.error(f"❌ 修改 Bash 脚本失败: {e}")
            return

        # 3. 运行
        cmd = f"bash run_evaluation_sca.sh"
        session_name = "stage2_sca"
        
        success, log_path = ProcessManager.run_with_log(cmd, session_name, self.ctx.root_dir)
        
        if success:
            self.set_state("last_log_path", log_path)
            st.success("🚀 Stage 2 (SCA) 任务已启动！请查看下方日志。")
            time.sleep(0.5)
            st.rerun()