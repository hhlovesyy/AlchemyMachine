# core/base_module.py
import streamlit as st
from abc import ABC, abstractmethod
from .context import GlobalContext 
from .process_mgr import ProcessManager
import os
import time
import streamlit.components.v1 as components
import html # 用于转义日志中的特殊字符

class BaseModule(ABC):
    def __init__(self):
        self.ctx = GlobalContext()
        self.name = "Unknown"
        self.icon = "📦"

    # --- 新增：简单的状态隔离 ---
    def get_state(self, key, default=None):
        # 给key加个前缀，防止跟其他模块冲突，比如 "CodeReader_filepath"
        full_key = f"{self.__class__.__name__}_{key}"
        return st.session_state.get(full_key, default)

    def set_state(self, key, value):
        full_key = f"{self.__class__.__name__}_{key}"
        st.session_state[full_key] = value
    # ---------------------------
    
    def render_log_monitor(self):
        st.divider()
        st.subheader("📋 实时日志监控")
        
        log_path = self.get_state("last_log_path")

        # 1. 控制栏
        c1, c2, c3 = st.columns([1.5, 1.5, 4])
        do_refresh = False
        with c1:
            if st.button("🔄 手动刷新", key=f"btn_refresh_{self.name}"):
                do_refresh = True
        with c2:
            auto_refresh = st.toggle("⚡ 自动刷新", value=False, key=f"toggle_{self.name}")
        with c3:
            if log_path:
                st.caption(f"Path: `{os.path.basename(log_path)}`")
            else:
                st.info("暂无记录")

        # 2. 读取日志
        # 这里读取的内容不需要清洗掉 ANSI 颜色代码其实更好，但为了兼容之前的逻辑，我们先读纯文本
        # 注意：为了配合自动滚动，我们这次不需要把内容倒序，就按正常顺序读
        raw_content = ProcessManager.read_log_tail(log_path, lines=200)

        # 如果你想过滤掉 [31m 这种颜色代码，取消下面这行的注释
        # raw_content = ProcessManager.clean_ansi_codes(raw_content)
        
        # 安全转义 (防止日志里有 < > 等符号破坏 HTML 结构)
        safe_content = html.escape(raw_content)

        # 3. 🔥 核心黑科技：使用 HTML/JS 容器替代 text_area 🔥
        # 我们构建一个 div，并注入一段 JS：window.scrollTo(0, document.body.scrollHeight);
        
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")

        html_code = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                /* 定义滚动条样式 (类似 Chrome/VSCode) */
                ::-webkit-scrollbar {{ width: 10px; height: 10px; }}
                ::-webkit-scrollbar-track {{ background: #1e1e1e; }}
                ::-webkit-scrollbar-thumb {{ background: #555; border-radius: 5px; }}
                ::-webkit-scrollbar-thumb:hover {{ background: #888; }}
                
                body {{
                    background-color: #0e1117; /* 匹配 Streamlit 深色背景 */
                    color: #d4d4d4;            /* 浅灰文字 */
                    font-family: 'Consolas', 'Courier New', monospace;
                    font-size: 13px;
                    margin: 0;
                    padding: 10px;
                    white-space: pre-wrap;     /* 保留换行和空格 */
                    word-wrap: break-word;
                }}
                .log-container {{
                    width: 100%;
                }}
            </style>
        </head>
        <body>
            <div class="log-container" id="log-box">
                {safe_content}
                <br><br>
                <span style="color: #666;">--- Last Updated: {timestamp} ---</span>
            </div>

            <script>
                // 🔥 核心 JS：每次加载都自动滚到底部 🔥
                window.scrollTo(0, document.body.scrollHeight);
            </script>
        </body>
        </html>
        """

        # 4. 渲染 HTML 组件
        # height=400 设置窗口高度，scrolling=True 允许组件内部滚动
        components.html(html_code, height=400, scrolling=True)

        # 5. 智能提示 (保持不变)
        if "Error" in raw_content or "Traceback" in raw_content:
            st.error("⚠️ 日志中包含报错信息")
        elif "Task Finished" in raw_content:
            st.success("✅ 任务已执行完毕")

        # 6. 自动刷新逻辑
        if auto_refresh or do_refresh:
            time.sleep(2)
            st.rerun()
    

    @abstractmethod
    def render_sidebar(self):
        pass

    @abstractmethod
    def render_main(self):
        pass
    
    def show(self):
        st.header(f"{self.icon} {self.name}")
        with st.sidebar:
            st.divider()
            self.render_sidebar()
        self.render_main()