import streamlit as st
import os
import glob
import math
from core.base import BaseModule

class VideoGalleryModule(BaseModule):
    def render_sidebar(self):
        st.subheader("📂 目录导航器")
        
        # 1. 路径管理
        default_root = "/root/autodl-tmp"
        current_path = self.get_state("current_path", default_root)

        if not os.path.exists(current_path):
            current_path = default_root
            self.set_state("current_path", current_path)

        st.caption("当前路径:")
        st.code(current_path, language="bash")
        
        # 2. 返回上一级
        parent_dir = os.path.dirname(current_path)
        col_up, col_root = st.columns([2, 1])
        with col_up:
            if st.button("⬆️ 返回上一级", use_container_width=True, key=self._get_key("return_step")):
                self.set_state("current_path", parent_dir)
                self.set_state("gallery_page", 1) # 换目录时重置页码
                st.rerun()
        with col_root:
            if st.button("🏠 根目录", use_container_width=True,key=self._get_key("return_root")):
                self.set_state("current_path", default_root)
                self.set_state("gallery_page", 1)
                st.rerun()

        st.divider()
        st.write("📁 **子文件夹:**")

        # 3. 子文件夹列表
        try:
            all_items = sorted(os.listdir(current_path))
            subdirs = [d for d in all_items if os.path.isdir(os.path.join(current_path, d)) and not d.startswith('.')]
            
            if subdirs:
                with st.container(height=400): # 固定高度滚动条，防止侧边栏太长
                    for d in subdirs:
                        if st.button(f"📂 {d}", key=self._get_key(f"dir_{d}"), use_container_width=True):
                            new_path = os.path.join(current_path, d)
                            self.set_state("current_path", new_path)
                            self.set_state("gallery_page", 1) # 切文件夹重置页码
                            st.rerun()
            else:
                st.caption("（无子文件夹）")
        except Exception as e:
            st.error(f"Error: {e}")

    def render_main(self):
        # --- 修复点：这里必须再次指定默认路径，防止返回 None ---
        default_root = "/root/autodl-tmp" 
        current_path = self.get_state("current_path", default_root)
        
        # --- 双重保险：如果拿到的是 None 或空字符串，强制设为默认值 ---
        if not current_path:
            current_path = default_root
        
        # 现在的 current_path 绝对不可能是 None 了，安全检查
        if not os.path.exists(current_path):
            st.error(f"路径不存在: {current_path}")
            return

        st.subheader(f"🎬 视频画廊")
        
        # 1. 扫描文件
        mp4_files = sorted(glob.glob(os.path.join(current_path, "*.mp4")))
        total_files = len(mp4_files)

        if total_files == 0:
            st.info("📭 当前目录下没有 MP4 视频。")
            return

        # ================== 🔥 核心优化：分页逻辑 ==================
        ITEMS_PER_PAGE = 9  # 每页显示 9 个视频 (3x3)
        total_pages = math.ceil(total_files / ITEMS_PER_PAGE)
        
        # 获取当前页码，默认为 1
        current_page = self.get_state("gallery_page", 1)
        
        # 简单的翻页器 UI
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            # 这是一个滑块或者数字输入框，用来翻页
            current_page = st.number_input(
                f"第几页 (共 {total_pages} 页, {total_files} 个视频)", 
                min_value=1, max_value=total_pages, value=current_page, key=self._get_key("gallery_pager")
            )
            # 保存页码状态，防止刷新重置
            if current_page != self.get_state("gallery_page"):
                self.set_state("gallery_page", current_page)
                st.rerun()

        st.divider()

        # 计算当前页要显示哪些文件
        start_idx = (current_page - 1) * ITEMS_PER_PAGE
        end_idx = start_idx + ITEMS_PER_PAGE
        page_files = mp4_files[start_idx:end_idx]

        # ================== 🔥 UI 瘦身：网格显示 ==================
        cols = st.columns(3) # 3列布局

        for i, video_path in enumerate(page_files):
            col = cols[i % 3] # 决定放在第几列
            file_name = os.path.basename(video_path)
            
            # 截断长文件名用于显示标题 (超过20字显示...)
            display_name = (file_name[:20] + '..') if len(file_name) > 20 else file_name
            
            with col:
                # 1. 先直接放视频，视觉重心
                st.video(video_path)
                
                # 2. 详情放在折叠框里，解决"下面东西太多"的问题
                with st.expander(f"📝 {display_name}", expanded=False, key=self._get_key(f"expander_{file_name}")):
                    st.caption(f"全名: {file_name}")
                    
                    # 3. 修复下载按钮：读取二进制数据
                    try:
                        with open(video_path, "rb") as f:
                            file_bytes = f.read()
                            st.download_button(
                                label="⬇️ 下载视频",
                                data=file_bytes,
                                file_name=file_name,
                                mime="video/mp4",
                                key=f"dl_{start_idx + i}", # 必须保证key唯一
                                use_container_width=True
                            )
                    except Exception as e:
                        st.error("文件读取失败")