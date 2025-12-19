# modules/point_selector.py
import streamlit as st
import os
import json
import pandas as pd
import io
import base64
import matplotlib.pyplot as plt
from PIL import Image
from streamlit_drawable_canvas import st_canvas
from core.base import BaseModule

# ================= 🔥 核心修复补丁 🔥 =================
# 这一段必须放在文件最前面
# 作用：手动定义被 Streamlit 移除的 image_to_url 函数
# 这样 st_canvas 就能正常工作了
import streamlit.elements.image as st_image

if not hasattr(st_image, 'image_to_url'):
    def custom_image_to_url(image, width, clamp, channels, output_format, image_id, allow_emoji=False):
        """
        手动实现的图片转 URL 函数 (Base64 版本)
        """
        # 如果不是 PIL 图片，直接返回空
        if not isinstance(image, Image.Image):
            return ""
        
        # 转 Base64
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/png;base64,{img_str}"

    # 注入补丁
    st_image.image_to_url = custom_image_to_url
# ====================================================

class PointSelectorModule(BaseModule):
    def __init__(self):
        super().__init__()
        self.name = "控制点编辑器"
        self.icon = "🎯"
        self.SAVE_PATH = os.path.join(self.ctx.root_dir, "control_points.json")
        
        # === 坐标系配置 ===
        self.CANVAS_SIZE = 600
        self.WORLD_RANGE = 20.0
        self.PIXELS_PER_METER = self.CANVAS_SIZE / self.WORLD_RANGE
        self.CENTER_PIXEL = self.CANVAS_SIZE / 2 

    def _generate_grid_background(self):
        """生成带中心坐标轴的背景图"""
        fig, ax = plt.subplots(figsize=(6, 6), dpi=100)
        
        limit = self.WORLD_RANGE / 2
        ax.set_xlim(-limit, limit)
        ax.set_ylim(-limit, limit)
        
        # 隐藏边框，移动轴到中心
        ax.spines['right'].set_color('none')
        ax.spines['top'].set_color('none')
        ax.spines['bottom'].set_position(('data', 0))
        ax.spines['left'].set_position(('data', 0))
        ax.spines['bottom'].set_color('black')
        ax.spines['left'].set_color('black')
        ax.spines['bottom'].set_linewidth(1.5)
        ax.spines['left'].set_linewidth(1.5)

        # 刻度设置
        import matplotlib.ticker as ticker
        ax.xaxis.set_major_locator(ticker.MultipleLocator(5))
        ax.yaxis.set_major_locator(ticker.MultipleLocator(5))
        ax.xaxis.set_minor_locator(ticker.MultipleLocator(1))
        ax.yaxis.set_minor_locator(ticker.MultipleLocator(1))
        
        ax.grid(which='major', color='#999999', linestyle='-', linewidth=1.0, alpha=0.4)
        ax.grid(which='minor', color='#cccccc', linestyle=':', linewidth=0.8, alpha=0.3)
        
        ax.set_xlabel('X (m)', loc='right', fontsize=10, weight='bold')
        ax.set_ylabel('Y (m)', loc='top', fontsize=10, weight='bold', rotation=0)

        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.05)
        buf.seek(0)
        img = Image.open(buf)
        plt.close(fig)
        
        # 调整大小以严格匹配 canvas
        img = img.resize((self.CANVAS_SIZE, self.CANVAS_SIZE))
        return img

    def _pixel_to_world(self, px, py):
        world_x = (px - self.CENTER_PIXEL) / self.PIXELS_PER_METER
        world_y = -(py - self.CENTER_PIXEL) / self.PIXELS_PER_METER
        return round(world_x, 2), round(world_y, 2)

    def render_sidebar(self):
        st.subheader("🎮 控制面板")
        st.info("""
        **坐标系说明**:
        - 原点 (0,0) 在正中心
        - X轴: 左右各 10 米
        - Y轴: 上下各 10 米
        """)
        
        mode = st.radio(
            "选择添加类型:",
            ("目标点 (Goal) 🟢", "避障点 (Obstacle) 🔴"),
            index=0
        )
        self.current_mode = "target" if "Goal" in mode else "obstacle"
        
        if self.current_mode == "target":
            self.draw_color = "rgba(0, 255, 0, 0.9)"
            self.point_radius = 8 
            st.caption("点击设置目标位置")
        else:
            self.draw_color = "rgba(255, 0, 0, 0.4)"
            real_radius = st.slider("障碍半径 (米)", 0.5, 5.0, 1.5, step=0.1)
            self.point_radius = int(real_radius * self.PIXELS_PER_METER)
            st.caption(f"显示半径: {real_radius}m")

        st.divider()
        st.button("🗑️ 刷新清空", on_click=lambda: st.rerun())

    def render_main(self):
        st.markdown("## 🎯 交互式控制点编辑器")

        col_canvas, col_data = st.columns([2, 1])

        # ================= 画布 =================
        with col_canvas:
            # 1. 生成图片对象 (PIL Image)
            bg_img = self._generate_grid_background()
            
            # 2. 调用 Canvas
            # 注意：这里我们传回了 bg_img (PIL对象)，因为我们已经在开头打好了补丁
            # 插件可以随意调节它的大小，也可以随意调用 image_to_url 了
            canvas_result = st_canvas(
                fill_color=self.draw_color,
                stroke_width=1,
                stroke_color="#fff",
                background_image=bg_img,  # 传 PIL 对象
                update_streamlit=True,
                height=self.CANVAS_SIZE,
                width=self.CANVAS_SIZE,
                drawing_mode="point", 
                point_display_radius=self.point_radius,
                key="canvas_coord_sys_final",
                display_toolbar=True,
            )

        # ================= 数据表格 =================
        with col_data:
            st.markdown("### 📝 已选点位")
            
            points_data = []
            
            if canvas_result.json_data is not None:
                objects = canvas_result.json_data["objects"]
                
                for i, obj in enumerate(objects):
                    px, py = obj["left"], obj["top"]
                    wx, wy = self._pixel_to_world(px, py)
                    w_radius = round(obj["radius"] / self.PIXELS_PER_METER, 2)
                    
                    p_type = "目标点" if "0, 255, 0" in obj.get("fill") else "障碍物"
                    
                    points_data.append({
                        "ID": i + 1,
                        "类型": p_type,
                        "X": wx,
                        "Y": wy,
                        "R (m)": w_radius if p_type == "障碍物" else "-"
                    })

            if points_data:
                df = pd.DataFrame(points_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                if st.button("💾 保存配置 (JSON)", type="primary", use_container_width=True):
                    self._save_points(points_data)
            else:
                st.caption("请在左侧坐标系中点击...")

    def _save_points(self, data):
        try:
            net_points = []
            for item in data:
                pt_type = "target" if item["类型"] == "目标点" else "obstacle"
                radius = item["R (m)"] if item["R (m)"] != "-" else 0.1
                
                net_points.append({
                    "type": pt_type,
                    "pos": [item["X"], item["Y"]],
                    "radius": float(radius)
                })
            
            final_json = {
                "meta": {"range": [-10, 10], "unit": "meter"},
                "points": net_points
            }
            
            with open(self.SAVE_PATH, 'w', encoding='utf-8') as f:
                json.dump(final_json, f, indent=4)
            
            st.success("✅ 保存成功！")
            st.code(json.dumps(net_points, indent=2), language="json")
        except Exception as e:
            st.error(f"保存失败: {e}")