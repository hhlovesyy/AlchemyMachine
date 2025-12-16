import streamlit as st
import os
import json
from core.base import BaseModule

class CodeReviewModule(BaseModule):
    def render_sidebar(self):
        st.subheader("📂 文件浏览器")
        
        # 1. 输入根路径 (带有记忆功能)
        default_root = self.get_state("root_dir", "/root/autodl-tmp/MyRepository")
        root_dir = st.text_input("代码根目录", default_root)
        self.set_state("root_dir", root_dir)

        # 2. 扫描文件
        if os.path.exists(root_dir):
            files = []
            for dp, dn, filenames in os.walk(root_dir):
                for f in filenames:
                    if f.endswith(('.py', '.yaml', '.sh', '.json')):
                        # 保存相对路径
                        full_path = os.path.join(dp, f)
                        rel_path = os.path.relpath(full_path, root_dir)
                        files.append(rel_path)
            
            selected_file = st.selectbox("选择文件", sorted(files))
            
            # 保存完整路径供主界面读取
            if selected_file:
                self.set_state("current_file", os.path.join(root_dir, selected_file))
        else:
            st.error("路径不存在")

    def render_main(self):
        current_file = self.get_state("current_file")
        
        if not current_file or not os.path.exists(current_file):
            st.info("👈 请先在左侧选择要阅读的文件")
            return

        # --- 布局：左边代码，右边笔记 ---
        col_code, col_notes = st.columns([2, 1])

        # A. 读取代码
        with open(current_file, 'r', encoding='utf-8') as f:
            code_content = f.read()

        with col_code:
            st.markdown(f"### `{os.path.basename(current_file)}`")
            # 显示带行号的代码块
            st.code(code_content, language='python', line_numbers=True)

        # B. 笔记/标记功能
        note_file = current_file + ".meta.json" # 简单的元数据存储方式
        
        # 加载旧笔记
        notes = {}
        if os.path.exists(note_file):
            try:
                with open(note_file, 'r') as f:
                    notes = json.load(f)
            except:
                pass

        with col_notes:
            st.subheader("📝 重点标记 (Annotations)")
            
            # 添加新笔记表单
            with st.form("add_note_form"):
                line_num = st.number_input("行号 (Line)", min_value=1, step=1)
                comment = st.text_area("备注内容", placeholder="这段代码很重要，因为...")
                if st.form_submit_button("➕ 添加/更新标记"):
                    notes[str(line_num)] = comment
                    with open(note_file, 'w') as f:
                        json.dump(notes, f, indent=4)
                    st.toast(f"行 {line_num} 标记已保存")
                    st.rerun() # 刷新显示

            st.divider()
            
            # 展示现有笔记
            if notes:
                st.write("📖 **现有标记:**")
                # 按行号排序显示
                sorted_lines = sorted(notes.keys(), key=lambda x: int(x))
                for line in sorted_lines:
                    with st.expander(f"Line {line}", expanded=True):
                        st.write(notes[line])
                        if st.button("🗑️ 删除", key=f"del_{line}"):
                            del notes[line]
                            with open(note_file, 'w') as f:
                                json.dump(notes, f, indent=4)
                            st.rerun()
            else:
                st.caption("暂无标记")