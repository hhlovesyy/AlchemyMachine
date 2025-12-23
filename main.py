# main.py 启动方法类似如下：streamlit run main.py --server.port 6006
import streamlit as st
from core.loader import load_config, load_active_modules
from core.context import GlobalContext
from core.live2d_helper import Live2DHelper 

# 1. 初始化
cfg = load_config()
st.set_page_config(page_title=cfg['settings']['title'], layout="wide", page_icon=cfg['settings']['icon'])
ctx = GlobalContext() # 初始化单例上下文
l2d = Live2DHelper() # 🔥 初始化 helper

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

# ==========================================
# 🔥 侧边栏底部：Live2D 设置与渲染
# ==========================================
with st.sidebar:
    st.divider() # 画一条线
    
    # 1. 搞一个折叠框，把设置藏起来，不占地儿
    with st.expander("🧚‍♀️ 炼丹伴侣设置", expanded=False):
        show_waifu = st.toggle("开启看板娘", value=True, key="global_waifu_toggle")
        
        # 2. 选人下拉框 (从 helper 获取列表)
        if show_waifu:
            model_list = l2d.get_available_models()
            # 记住用户的选择
            selected_model = st.selectbox(
                "更换角色", 
                model_list, 
                index=0, 
                key="global_waifu_select"
            )
        else:
            selected_model = None

    # 3. 🔥 核心修复：在这里渲染小人！🔥
    # 放在 sidebar 的最后，这样它就永远固定在左侧导航栏的底部
    # 不会因为右边主界面内容太多而被挤丢
    if show_waifu:
        # 获取当前心情 (由各模块 set_live2d_state 控制)
        current_state = st.session_state.get("live2d_state", "idle")
        
        # 渲染！
        l2d.show(state=current_state, model_name=selected_model)

# 4. 🔥 核心调用：执行模板方法
# 这里调用 show()，它会自动安排 render_sidebar 和 render_main
current_module.show()
