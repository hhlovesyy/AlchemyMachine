import streamlit as st
import os
import json
import io
import base64
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from PIL import Image
from streamlit_drawable_canvas import st_canvas
from core.base import BaseModule

# 尝试导入路径规划器
try:
    from core.path_planner import PathPlanner
    HAS_PLANNER = True
except ImportError as e:
    HAS_PLANNER = False
    print(f"Algo Error: {e}")

# ================= 🔥 Monkey Patch (保持不动) 🔥 =================
import streamlit.elements.image as st_image
if not hasattr(st_image, 'image_to_url'):
    def custom_image_to_url(image, width, clamp, channels, output_format, image_id, allow_emoji=False):
        if not isinstance(image, Image.Image): return ""
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/png;base64,{img_str}"
    st_image.image_to_url = custom_image_to_url
# ==============================================================

class PointSelectorModule(BaseModule):
    def __init__(self):
        super().__init__()
        self.name = "轨迹与环境编辑器"
        self.icon = "🗺️"
        self.SAVE_PATH = os.path.join(self.ctx.root_dir, "task_config.json")
        
        # 坐标配置
        self.CANVAS_SIZE = 600   
        self.WORLD_RANGE = 20.0  
        self.PX_PER_M = self.CANVAS_SIZE / self.WORLD_RANGE 
        self.CENTER = self.CANVAS_SIZE / 2 
        
        # 缓存静态背景
        if 'static_bg_img' not in st.session_state:
            st.session_state.static_bg_img = self._generate_static_grid()

    def _generate_static_grid(self):
        """生成纯净的坐标网格背景"""
        fig, ax = plt.subplots(figsize=(6, 6), dpi=100)
        limit = self.WORLD_RANGE / 2
        ax.set_xlim(-limit, limit)
        ax.set_ylim(-limit, limit)
        
        ax.spines['right'].set_color('none')
        ax.spines['top'].set_color('none')
        ax.spines['bottom'].set_position(('data', 0))
        ax.spines['left'].set_position(('data', 0))
        ax.spines['bottom'].set_color('black')
        ax.spines['left'].set_color('black')

        import matplotlib.ticker as ticker
        ax.xaxis.set_major_locator(ticker.MultipleLocator(5))
        ax.yaxis.set_major_locator(ticker.MultipleLocator(5))
        ax.grid(which='major', color='#999999', linestyle='-', alpha=0.3)
        
        ax.set_xlabel('X (m)', loc='right')
        ax.set_ylabel('Z (m)', loc='top', rotation=0)

        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.02)
        buf.seek(0)
        img = Image.open(buf)
        plt.close(fig)
        img = img.resize((self.CANVAS_SIZE, self.CANVAS_SIZE))
        return img

    def _plot_preview_result(self, raw_pts, raw_obs, planned_path):
        """生成预览结果图"""
        fig, ax = plt.subplots(figsize=(5, 5), dpi=100)
        limit = self.WORLD_RANGE / 2
        ax.set_xlim(-limit, limit)
        ax.set_ylim(-limit, limit)
        ax.set_aspect('equal')
        
        # 网格
        ax.grid(True, linestyle='--', alpha=0.3)
        ax.axhline(0, color='black', linewidth=1)
        ax.axvline(0, color='black', linewidth=1)
        
        # 1. 画障碍物
        for obs in raw_obs:
            cx, cy = obs['center']
            if obs['type'] == 'cylinder':
                c = plt.Circle((cx, cy), obs['radius'], color='red', alpha=0.4, label='Obstacle' if 'Obstacle' not in [l.get_label() for l in ax.patches] else "")
                ax.add_patch(c)
                c_out = plt.Circle((cx, cy), obs['radius'], color='red', fill=False)
                ax.add_patch(c_out)
            elif obs['type'] == 'box':
                w, d = obs['extent']
                rect_x = cx - w/2
                rect_y = cy - d/2
                r = patches.Rectangle((rect_x, rect_y), w, d, linewidth=1, edgecolor='blue', facecolor='blue', alpha=0.4, label='Obstacle' if 'Obstacle' not in [l.get_label() for l in ax.patches] else "")
                ax.add_patch(r)
            
        # 2. 画轨迹点
        if len(raw_pts) > 0:
            pts = np.array(raw_pts)
            ax.scatter(pts[:, 0], pts[:, 1], c='green', s=50, label='Waypoints', zorder=5)
            ax.plot(pts[:, 0], pts[:, 1], 'g--', alpha=0.3)

        # 3. 画规划路径
        if planned_path is not None and len(planned_path) > 1:
            px = planned_path[:, 0]
            py = planned_path[:, 1]
            ax.plot(px, py, color='#1E90FF', linewidth=2.5, label='Planner Path')
            
        # 🔥 修复警告：只有当有图例项时才调用 legend
        handles, labels = ax.get_legend_handles_labels()
        if handles:
            ax.legend(loc='upper right', fontsize='x-small')
            
        ax.set_title("Real-time Preview (XZ Plane)", fontsize=10)
        return fig

    def render_sidebar(self):
        st.subheader("📝 任务参数")
        with st.form("global_config"):
            self.proj_name = st.text_input("Project Name", "Demo_Task_01")
            self.motion_val = st.text_input("Motion ID", "000021")
            st.form_submit_button("💾 更新")

        st.divider()
        st.subheader("🎨 绘图工具")
        
        # 默认高度，防止未选择障碍物模式时报错
        self.obs_height = 2.0 
        
        self.draw_mode = st.radio(
            "绘制对象:", 
            ("📍 轨迹点 (Green)", "🧱 圆柱 (Red Cylinder)", "📦 长方体 (Blue Box)")
        )
        
        if "轨迹" in self.draw_mode:
            self.canvas_mode = "point"
            self.stroke_color = "#00FF00"
            self.point_radius = 6
            st.caption("点击添加路径点")
            
        elif "圆柱" in self.draw_mode:
            self.canvas_mode = "point"
            self.stroke_color = "#FF0000"
            self.obs_radius_m = st.slider("圆柱半径 (m)", 0.2, 3.0, 0.5, step=0.1)
            self.point_radius = int(self.obs_radius_m * self.PX_PER_M)
            self.obs_height = st.number_input("圆柱高度 (m)", value=2.0)
            
        elif "长方体" in self.draw_mode:
            self.canvas_mode = "rect"
            self.stroke_color = "#0000FF"
            self.point_radius = 6 
            self.obs_height = st.number_input("长方体高度 (m)", value=1.0)
            st.info("拖拽画矩形")

        st.divider()
        
        if HAS_PLANNER:
            self.show_algo = st.toggle("开启路径预览", value=True)
            if self.show_algo:
                self.algo_margin = st.slider("避障安全距离 (m)", 0.0, 1.0, 0.3)
        else:
            self.show_algo = False
            
        st.button("🗑️ 清空画布", on_click=lambda: st.rerun())

    def render_main(self):
        st.markdown("## 🗺️ 场景编辑器")
        col_input, col_output = st.columns([1, 1])
        
        raw_pts = []
        raw_obs = []
        planned_path_arr = None

        # ================= 左侧：输入画布 =================
        with col_input:
            st.markdown("### 👈 第一步：在此绘制")
            bg_img = st.session_state.static_bg_img
            
            canvas_result = st_canvas(
                fill_color=self.stroke_color,
                stroke_width=2,
                stroke_color="#fff",
                background_image=bg_img,
                update_streamlit=True,
                height=self.CANVAS_SIZE,
                width=self.CANVAS_SIZE,
                drawing_mode=self.canvas_mode,
                point_display_radius=self.point_radius,
                key="scene_editor_input",
                display_toolbar=True,
            )

        # ================= 数据解析 =================
        if canvas_result.json_data is not None:
            objects = canvas_result.json_data["objects"]
            for obj in objects:
                obj_type = obj.get("type") 
                fill_color = obj.get("fill")
                px, py = obj["left"], obj["top"]
                
                if obj_type == "circle" or obj_type == "point":
                    wx = (px - self.CENTER) / self.PX_PER_M
                    wz = -(py - self.CENTER) / self.PX_PER_M
                    
                    if "#00FF00" in fill_color: 
                        raw_pts.append([wx, wz])
                    else: 
                        r_m = obj["radius"] / self.PX_PER_M
                        raw_obs.append({
                            "type": "cylinder",
                            "center": [wx, wz], 
                            "radius": r_m
                        })
                        
                elif obj_type == "rect":
                    w_px = obj["width"] * obj["scaleX"]
                    h_px = obj["height"] * obj["scaleY"]
                    cx_px = px + w_px / 2
                    cy_px = py + h_px / 2
                    
                    wx = (cx_px - self.CENTER) / self.PX_PER_M
                    wz = -(cy_px - self.CENTER) / self.PX_PER_M
                    w_m = w_px / self.PX_PER_M
                    d_m = h_px / self.PX_PER_M
                    
                    raw_obs.append({
                        "type": "box",
                        "center": [wx, wz],
                        "extent": [w_m, d_m]
                    })

        # ================= 算法计算 =================
        if self.show_algo and len(raw_pts) >= 2:
            try:
                planner = PathPlanner(world_range=self.WORLD_RANGE, margin=self.algo_margin)
                planned_path_arr = planner.generate_path(raw_pts, raw_obs)
            except Exception as e:
                st.error(f"算法错误: {e}")

        # ================= 右侧：结果预览 =================
        with col_output:
            st.markdown("### 👉 第二步：结果预览")
            fig = self._plot_preview_result(raw_pts, raw_obs, planned_path_arr)
            st.pyplot(fig)

            st.divider()
            with st.expander("📄 JSON 配置预览", expanded=True):
                obstacles_json = []
                for i, obs in enumerate(raw_obs):
                    item = {
                        "id": f"obs_{i}",
                        "type": obs['type'],
                        "center": [round(obs['center'][0], 2), round(obs['center'][1], 2)],
                    }
                    if obs['type'] == 'cylinder':
                        item['radius'] = round(obs['radius'], 2)
                    elif obs['type'] == 'box':
                        w, d = obs['extent']
                        item['extent'] = [round(w, 2), round(d, 2)]
                    
                    # 🔥 修复 AttributeError: 使用 getattr 或默认值 🔥
                    # 这样即使在"轨迹"模式下，这里也能取到默认的 2.0，不会报错
                    item['height'] = getattr(self, 'obs_height', 2.0)
                    
                    obstacles_json.append(item)
                
                traj_json = [[round(p[0], 2), round(p[1], 2)] for p in raw_pts]
                
                final_json = {
                    "project_name": self.proj_name,
                    "environment": {"obstacles": obstacles_json},
                    "trajectory": {
                        "type": "bezier_control_points",
                        "points": traj_json,
                        "preview_valid": planned_path_arr is not None
                    }
                }
                
                st.json(final_json)
                
                if st.button("💾 保存 Task JSON", type="primary", use_container_width=True):
                    self._save_json(final_json)

    def _save_json(self, data):
        try:
            with open(self.SAVE_PATH, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            st.success(f"✅ 保存成功: {self.SAVE_PATH}")
        except Exception as e:
            st.error(f"保存失败: {e}")