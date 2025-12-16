# main.py
import streamlit as st
from core.loader import load_config, load_active_modules
from core.context import GlobalContext

# 1. 初始化
cfg = load_config()
st.set_page_config(page_title=cfg['settings']['title'], layout="wide", page_icon=cfg['settings']['icon'])
ctx = GlobalContext() # 初始化单例上下文

# 2. 动态加载
modules_map = load_active_modules(cfg)

# 3. 侧边栏导航
st.sidebar.title(cfg['settings']['title'])

if not modules_map:
    st.error("⚠️ 未加载任何模块，请检查 app_config.yaml")
    st.stop()

# 自动生成菜单
selected_key = st.sidebar.radio("功能导航", list(modules_map.keys()))
current_module = modules_map[selected_key]

# 4. 🔥 核心调用：执行模板方法
# 这里调用 show()，它会自动安排 render_sidebar 和 render_main
current_module.show()