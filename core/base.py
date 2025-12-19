# core/base.py
import streamlit as st
from abc import ABC, abstractmethod
from .context import GlobalContext 
from .process_mgr import ProcessManager
import os
import time
import streamlit.components.v1 as components
from ansi2html import Ansi2HTMLConverter # 需要 pip install ansi2html

class BaseModule(ABC):
    def __init__(self):
        self.ctx = GlobalContext()
        self.name = "Unknown"
        self.icon = "📦"
        # 初始化转换器 (黑底白字)
        self.conv = Ansi2HTMLConverter(dark_bg=True, scheme='xterm', inline=True)

    def get_state(self, key, default=None):
        full_key = f"{self.__class__.__name__}_{key}"
        return st.session_state.get(full_key, default)

    def set_state(self, key, value):
        full_key = f"{self.__class__.__name__}_{key}"
        st.session_state[full_key] = value
    
    def render_log_monitor(self):
        st.divider()
        st.subheader("📋 实时终端监控 (Live Terminal)")
        
        log_path = self.get_state("last_log_path")

        # 1. 控制栏
        c1, c2, c3 = st.columns([1, 1.5, 5])
        with c1:
            if st.button("🔄 刷新", key=f"btn_r_{self.name}"):
                pass
        with c2:
            # 默认开启自动刷新，为了看进度条
            auto_refresh = st.toggle("⚡ 自动同步", value=True, key=f"tog_{self.name}")
        with c3:
            if log_path:
                st.caption(f"Watching: `{os.path.basename(log_path)}`")
            else:
                st.info("等待任务启动...")

        # 2. 读取日志 (已在 ProcessManager 里处理了 \r 回车符)
        raw_content = ProcessManager.read_log_tail(log_path, lines=150)

        # 3. 转换为 HTML (保留颜色!)
        # 将 \n 转换为 <br>，并处理颜色代码
        try:
            html_content = self.conv.convert(raw_content, full=False)
        except:
            html_content = f"<pre>{raw_content}</pre>"

        # 4. 渲染 CSS 样式，模仿 VSCode 终端
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")

        custom_css = """
        <style>
            body {
                background-color: #1e1e1e;
                color: #cccccc;
                font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
                font-size: 12px;
                margin: 0; padding: 10px;
                line-height: 1.2;
            }
            .ansi2html-content { white-space: pre-wrap; word-break: break-all; }
            /* 隐藏 ansi2html 生成的头信息 */
            .original-src { display: none; }
        </style>
        """

        final_html = f"""
        <!DOCTYPE html>
        <html>
        <head>{custom_css}</head>
        <body>
            <div id="term-box">
                {html_content}
                <div style="margin-top:10px; color:#666; border-top:1px dashed #444; padding-top:5px;">
                    > Last Sync: {timestamp} (Auto-scroll enabled)
                </div>
            </div>
            <script>
                window.scrollTo(0, document.body.scrollHeight);
            </script>
        </body>
        </html>
        """

        # 5. 显示
        components.html(final_html, height=450, scrolling=True)

        # 6. 自动刷新逻辑
        if auto_refresh:
            time.sleep(1) # 每1秒刷新一次，模拟实时感
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