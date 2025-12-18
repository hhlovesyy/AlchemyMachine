# modules/inference.py
import streamlit as st
import os
import glob
import re
import time
from core.base import BaseModule
from core.utils import load_yaml, save_yaml
from core.process_mgr import ProcessManager

class InferenceModule(BaseModule):
    def __init__(self):
        super().__init__()
        self.name = "推理模式 (Inference)"
        self.icon = "🔮"
        
        # 场景预设
        self.SCENE_DESCRIPTIONS = {
            "Dumuqiao (独木桥)": "Walking on a narrow bridge.",
            "DiAiTongDao (低矮通道)": "Crouching while walking.",
            "ShuiKengDiMian (水坑地面)": "Walking on muddy ground.",
            "BoLiFangJian (玻璃房间)": "Walking in a glass room.",
            "T_Stage (T台走秀)": "Fashion model walking.",
            "CroudedPlace (拥挤场合)": "Walking through a crowd.",
            "DiAiTianhuaban (低矮天花板)": "Walking under a low ceiling.",
            "Bar (酒吧/醉酒)": "Drunk walking.",
            "WalkInSnowOrSand (雪地/沙地)": "Walking in deep snow.",
            "Dark (摸黑)": "Walking in the dark.",
            "LeanLeft (左倾)": "Leaning left.",
            "WetFloor (潮湿地面)": "Slippery floor.",
            "BaoFengYu (暴风雨)": "Walking in strong wind.",
            "IcyRoad (冰面)": "Walking on ice.",
            "Custom (自定义)": ""
        }

    def render_sidebar(self):
        st.subheader("🔮 推理参数配置")
        
        # === 1. 模型选择 ===
        st.markdown("#### 1. 模型权重")
        exp_root = os.path.join(self.ctx.root_dir, "experiments", "mld")
        if os.path.exists(exp_root):
            exps = sorted(os.listdir(exp_root), key=lambda x: os.path.getmtime(os.path.join(exp_root, x)), reverse=True)
        else:
            exps = []

        if not exps:
            st.error("⚠️ 未找到实验记录")
            return

        self.selected_exp = st.selectbox("选择实验", exps, key="inf_exp_sb")
        self.exp_path = os.path.join(exp_root, self.selected_exp)

        # Checkpoint
        ckpt_dir = os.path.join(self.exp_path, "checkpoints")
        ckpt_names = []
        if os.path.exists(ckpt_dir):
            ckpts = glob.glob(os.path.join(ckpt_dir, "*.ckpt"))
            ckpt_names = [os.path.basename(c) for c in ckpts]
            # 还原正则排序功能
            ckpt_names = sorted(ckpt_names, key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 0, reverse=True)

        self.selected_ckpt_name = st.selectbox("选择 Checkpoint", ckpt_names, key="inf_ckpt_sb")
        self.selected_ckpt_path = os.path.join(ckpt_dir, self.selected_ckpt_name) if self.selected_ckpt_name else None

        st.divider()

        # === 2. 场景与Hack ===
        st.markdown("#### 2. 场景与注入")
        scene_key = st.selectbox("场景预设", list(self.SCENE_DESCRIPTIONS.keys()), key="inf_scene_sb")
        
        # 自动填充 Prompt
        default_prompt = self.SCENE_DESCRIPTIONS[scene_key]
        if scene_key.startswith("Custom"):
            default_prompt = "Walking carefully."
        self.prompt_text = st.text_area("Prompt", default_prompt, height=70, key="inf_prompt_sb")
        self.scene_short_name = scene_key.split(' ')[0]

        # === 3. 数据与Scalar ===
        demo_root = os.path.join(self.ctx.root_dir, "demo")
        demo_subdirs = [d for d in os.listdir(demo_root) if os.path.isdir(os.path.join(demo_root, d))] if os.path.exists(demo_root) else ["Final_figure_content"]
        
        self.content_dir_name = st.selectbox("Content Source", demo_subdirs, index=0)
        self.style_dir_name = st.selectbox("Style Source", demo_subdirs, index=min(1, len(demo_subdirs)-1))
        
        st.markdown("---")
        # 还原 "The Hack"
        self.scene_scalar = st.number_input(
            "🔥 FiLM Scalar (注入源码)", 
            value=3.0, step=0.1, 
            help="此数值将直接注入到 mld.py 中，控制 FiLM 融合强度"
        )

    def render_main(self):
        # 如果没选 Checkpoint，提示用户
        if not hasattr(self, 'selected_ckpt_path') or not self.selected_ckpt_path:
            st.info("👈 请先在左侧侧边栏选择模型权重")
            return

        st.markdown(f"### 🪄 推理控制台")
        
        # === 信息展示卡片 ===
        with st.container():
            c1, c2, c3 = st.columns([2, 2, 1])
            with c1:
                st.caption("Current Model")
                st.code(self.selected_exp, language="text")
            with c2:
                st.caption("Target Checkpoint")
                st.code(self.selected_ckpt_name, language="text")
            with c3:
                st.caption("Scalar (FiLM)")
                st.code(str(self.scene_scalar), language="text")

        st.info(f"📝 **Prompt:** {self.prompt_text}")

        # === 结果路径提示 (还原你的要求) ===
        results_dir = os.path.join(self.ctx.root_dir, "results", "mld", self.selected_exp)
        with st.expander("📂 结果将保存在哪里？(点击查看)"):
            st.markdown(f"""
            推理结果将生成在以下目录：
            - **路径**: `{results_dir}`
            - **文件名前缀**: `inference_{self.scene_short_name}`
            
            你可以运行结束后，去 **"👀 看看你的：渲染"** 模块或者直接在文件系统中查看。
            """)

        # === 运行按钮 ===
        st.divider()
        col_btn, col_blank = st.columns([1, 4])
        with col_btn:
            run_btn = st.button("🚀 立即运行", type="primary", use_container_width=True)

        if run_btn:
            self.run_inference()

        # === 日志组件 ===
        self.render_log_monitor()

    def run_inference(self):
        # 1. 注入 Hack 代码 (FiLM Scalar)
        # 这里对应你说的 “执行的时候会把这个film也改了”
        if self._inject_hack_code(self.scene_scalar):
            # 2. 准备配置与命令
            self._execute_process()

    def _inject_hack_code(self, scalar_value):
        """修改 mld.py 源码，注入 scene_scalar"""
        mld_py_path = os.path.join(self.ctx.root_dir, "mld/models/modeltype/mld.py")
        
        if not os.path.exists(mld_py_path):
            st.error(f"❌ 找不到源码文件: {mld_py_path}")
            return False
            
        try:
            with open(mld_py_path, 'r', encoding='utf-8') as f:
                code_content = f.read()
            
            # 正则替换 DEFAULT_SCALAR_VAL = ...
            new_code = re.sub(
                r"DEFAULT_SCALAR_VAL\s*=\s*[\d\.]+", 
                f"DEFAULT_SCALAR_VAL = {scalar_value}", 
                code_content
            )
            
            with open(mld_py_path, 'w', encoding='utf-8') as f:
                f.write(new_code)
            
            # 显式告诉用户改了哪里
            st.toast(f"✅ 已修改 FiLM 参数: mld.py -> {scalar_value}", icon="💉")
            st.warning(f"⚠️ 注意: mld.py 源码中的 DEFAULT_SCALAR_VAL 已被修改为 {scalar_value}")
            return True

        except Exception as e:
            st.error(f"❌ 源码注入失败: {e}")
            return False

    def _execute_process(self):
        # 寻找 yaml
        launcher_yaml = os.path.join(self.exp_path, "launcher_config.yaml")
        if not os.path.exists(launcher_yaml):
            yamls = glob.glob(os.path.join(self.exp_path, "*.yaml"))
            launcher_yaml = yamls[0] if yamls else None
        
        if not launcher_yaml:
            st.error("❌ 找不到 yaml 配置文件")
            return

        # 修改 yaml
        inf_config = load_yaml(launcher_yaml)
        if 'TEST' not in inf_config: inf_config['TEST'] = {}
        inf_config['TEST']['CHECKPOINTS'] = self.selected_ckpt_path
        inf_config['TEST']['MULTI_MODAL_TYPE'] = 'text'
        inf_config['TEST']['MULTI_MODAL_TEXT_PROMPT'] = self.prompt_text
        
        temp_inf_yaml = os.path.join(self.exp_path, f"inference_{self.scene_short_name}.yaml")
        save_yaml(inf_config, temp_inf_yaml)
        
        # 构造命令
        content_dir = os.path.join("demo", self.content_dir_name)
        style_dir = os.path.join("demo", self.style_dir_name)
        
        script_name = "demo_transfer_with_scene.py"
        cmd = (
            f"python -u {script_name} "
            f"--cfg {temp_inf_yaml} "
            f"--cfg_assets {self.ctx.assets_file} "
            f"--content_motion_dir {content_dir} "
            f"--style_motion_dir {style_dir} "
            f"--scale 2.5"
        )
        
        session_name = f"inf_{self.scene_short_name}"[:20]
        
        # 运行
        success, msg = ProcessManager.run_with_log(
            command=cmd,
            task_name=session_name,
            root_dir=self.ctx.root_dir
        )
        
        if success:
            self.set_state("last_log_path", msg)
            st.toast("🚀 任务已启动！")
            
            # 显示结果预期位置
            result_expected = os.path.join(self.ctx.root_dir, "results", "mld", self.selected_exp)
            st.success(f"📂 任务结束后，结果将保存在: `{result_expected}`")
            
            time.sleep(1)
            st.rerun()
        else:
            st.error(f"启动失败: {msg}")