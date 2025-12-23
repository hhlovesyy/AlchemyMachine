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

try:
    from core.path_planner import PathPlanner
    HAS_PLANNER = True
except ImportError as e:
    HAS_PLANNER = False
    print(f"Algo Error: {e}")

# ================= 🔥 Monkey Patch 🔥 =================
import streamlit.elements.image as st_image
if not hasattr(st_image, 'image_to_url'):
    def custom_image_to_url(image, width, clamp, channels, output_format, image_id, allow_emoji=False):
        if not isinstance(image, Image.Image): return ""
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/png;base64,{img_str}"
    st_image.image_to_url = custom_image_to_url
# ======================================================

class PointSelectorModule(BaseModule):
    def __init__(self):
        super().__init__()
        self.name = "轨迹与环境编辑器"
        self.icon = "🗺️"
        self.SAVE_PATH = os.path.join(self.ctx.root_dir, "task_config.json")
        
        # 画布像素固定，但物理含义(WORLD_RANGE)现在变成动态的了
        self.CANVAS_SIZE = 600   
        self.CENTER = self.CANVAS_SIZE / 2 

    def _generate_grid_background(self, world_range, overlay_path=None):
        """生成背景图 (根据动态的 world_range)"""
        fig, ax = plt.subplots(figsize=(6, 6), dpi=100)
        
        limit = world_range / 2.0
        ax.set_xlim(-limit, limit)
        ax.set_ylim(-limit, limit)
        
        # 坐标轴
        ax.spines['right'].set_color('none')
        ax.spines['top'].set_color('none')
        ax.spines['bottom'].set_position(('data', 0))
        ax.spines['left'].set_position(('data', 0))
        ax.spines['bottom'].set_color('black')
        ax.spines['left'].set_color('black')
        ax.spines['bottom'].set_linewidth(1.2)
        ax.spines['left'].set_linewidth(1.2)

        import matplotlib.ticker as ticker
        # 动态调整刻度密度：大约每 1/4 范围一个主刻度
        step = int(world_range / 4)
        if step < 1: step = 1
        ax.xaxis.set_major_locator(ticker.MultipleLocator(step))
        ax.yaxis.set_major_locator(ticker.MultipleLocator(step))
        
        ax.grid(which='major', color='#999999', linestyle='-', alpha=0.3)
        ax.set_xlabel('X (m)', loc='right', fontsize=9)
        ax.set_ylabel('Z (m)', loc='top', fontsize=9, rotation=0)

        # 绘制路径
        if overlay_path is not None and len(overlay_path) > 1:
            px = overlay_path[:, 0]
            py = overlay_path[:, 1]
            ax.plot(px, py, color='#1E90FF', linewidth=2.5, linestyle='-', alpha=0.9)
            if len(px) > 2:
                ax.arrow(px[-2], py[-2], px[-1]-px[-2], py[-1]-py[-2], 
                         head_width=limit*0.05, color='#1E90FF', length_includes_head=True)

        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.02)
        buf.seek(0)
        img = Image.open(buf)
        plt.close(fig)
        img = img.resize((self.CANVAS_SIZE, self.CANVAS_SIZE))
        return img

    def _plot_preview_result(self, world_range, raw_pts, raw_obs, planned_path):
        """生成右侧预览图"""
        fig, ax = plt.subplots(figsize=(5, 5), dpi=100)
        limit = world_range / 2.0
        ax.set_xlim(-limit, limit)
        ax.set_ylim(-limit, limit)
        ax.set_aspect('equal')
        
        ax.grid(True, linestyle='--', alpha=0.3)
        ax.axhline(0, color='black', linewidth=1)
        ax.axvline(0, color='black', linewidth=1)
        
        for obs in raw_obs:
            cx, cy = obs['center']
            if obs['type'] == 'cylinder':
                c = plt.Circle((cx, cy), obs['radius'], color='red', alpha=0.4, label='Obstacle' if 'Obstacle' not in [l.get_label() for l in ax.patches] else "")
                ax.add_patch(c)
            elif obs['type'] == 'box':
                w, d = obs['extent']
                r = patches.Rectangle((cx - w/2, cy - d/2), w, d, color='blue', alpha=0.4, label='Obstacle' if 'Obstacle' not in [l.get_label() for l in ax.patches] else "")
                ax.add_patch(r)
            
        if len(raw_pts) > 0:
            pts = np.array(raw_pts)
            ax.scatter(pts[:, 0], pts[:, 1], c='green', s=50, label='Waypoints', zorder=5)
            ax.plot(pts[:, 0], pts[:, 1], 'g--', alpha=0.3)

        if planned_path is not None and len(planned_path) > 1:
            px = planned_path[:, 0]
            py = planned_path[:, 1]
            ax.plot(px, py, color='#1E90FF', linewidth=2.5, label='Planner')
            
        handles, labels = ax.get_legend_handles_labels()
        if handles: ax.legend(loc='upper right', fontsize='x-small')
        ax.set_title(f"Preview (Range: {int(world_range)}m)", fontsize=10)
        return fig

    def render_sidebar(self):
        st.subheader("📝 任务参数")
        with st.form(key=f"{self.name}_config_form"):
            self.proj_name = st.text_input("Project Name", "Demo_Task_01", key=self._get_key("proj_name"))
            self.motion_val = st.text_input("Motion ID", "000021", key=self._get_key("moion_val"))
            st.form_submit_button("💾 更新")

        st.divider()
        st.subheader("🎨 绘图工具")
        
        # === 🔥 新增：范围控制开关 🔥 ===
        use_default_range = st.checkbox("🔒 锁定视图范围 (20m)", value=False, key=self._get_key("use_default_range"))
        
        if use_default_range:
            self.current_world_range = 20.0
        else:
            self.current_world_range = st.number_input(
                "🌍 地图尺寸 (米)", 
                min_value=10.0, max_value=200.0, value=20.0, step=10.0,
                help="设置画布代表的物理范围。例如设为 40，则范围是 -20到20。",
                key=self._get_key("current_world_range")
            )
        
        # 动态计算比例尺
        self.px_per_m = self.CANVAS_SIZE / self.current_world_range
        # ==========================================

        self.obs_height = 2.0 
        self.draw_mode = st.radio("绘制对象:", ("📍 轨迹点 (Green)", "🧱 圆柱 (Red Cylinder)", "📦 长方体 (Blue Box)"), key=self._get_key("draw_mode"))
        
        if "轨迹" in self.draw_mode:
            self.canvas_mode = "point"
            self.stroke_color = "#00FF00"
            self.point_radius = 6
        elif "圆柱" in self.draw_mode:
            self.canvas_mode = "point"
            self.stroke_color = "#FF0000"
            self.obs_radius_m = st.slider("圆柱半径 (m)", 0.2, 5.0, 0.5, step=0.1)
            self.point_radius = int(self.obs_radius_m * self.px_per_m)
            self.obs_height = st.number_input("圆柱高度 (m)", value=2.0, key=self._get_key("obs_cylinder_height"))
        elif "长方体" in self.draw_mode:
            self.canvas_mode = "rect"
            self.stroke_color = "#0000FF"
            self.point_radius = 6 
            self.obs_height = st.number_input("长方体高度 (m)", value=1.0, key=self._get_key("obs_rect_height"))

        st.divider()
        
        if HAS_PLANNER:
            self.show_algo = st.toggle("开启路径预览", value=True, key=self._get_key("show_algo"))
            if self.show_algo:
                with st.expander("🛠️ 算法高级参数", expanded=True):
                    self.algo_margin = st.slider("1. 避障安全距离 (Margin)", 0.0, 3.0, 0.8, 0.1, key=self._get_key("algo_margin"))
                    self.algo_epsilon = st.slider("2. 路径简化 (Simplify)", 0.0, 2.0, 0.3, 0.1, key=self._get_key("algo_epsilon"))
                    self.algo_smooth = st.slider("3. 曲线平滑 (Smooth)", 0.0, 3.0, 0.5, 0.1, key=self._get_key("algo_smooth"))
        else:
            self.show_algo = False
            
        st.button("🗑️ 清空画布", on_click=lambda: st.rerun(), key=self._get_key("clear_drawing"))

    def render_main(self):
        st.markdown("## 🗺️ 场景编辑器")
        col_input, col_output = st.columns([1, 1])
        
        raw_pts = []
        raw_obs = []
        planned_path_arr = None

        # ================= 左侧 =================
        with col_input:
            st.markdown("### 👈 第一步：在此绘制")
            # 传入动态的 range
            bg_img = self._generate_grid_background(world_range=self.current_world_range, overlay_path=None)
            
            # 由于背景可能因为range变化而变化，这里 key 最好绑定 range，强迫重绘
            canvas_key = f"scene_editor_input_{int(self.current_world_range)}"
            
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
                key=self._get_key("scene_editor_main"), # 保持key不变以维持session状态
                display_toolbar=True,
            )

        # ================= 数据解析 =================
        if canvas_result.json_data is not None:
            objects = canvas_result.json_data["objects"]
            for obj in objects:
                obj_type = obj.get("type") 
                fill_color = obj.get("fill")
                px, py = obj["left"], obj["top"]
                
                # 使用动态的 px_per_m 进行转换
                if obj_type == "circle" or obj_type == "point":
                    wx = (px - self.CENTER) / self.px_per_m
                    wz = -(py - self.CENTER) / self.px_per_m
                    
                    if "#00FF00" in fill_color: 
                        raw_pts.append([wx, wz])
                    else: 
                        r_m = obj["radius"] / self.px_per_m
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
                    
                    wx = (cx_px - self.CENTER) / self.px_per_m
                    wz = -(cy_px - self.CENTER) / self.px_per_m
                    w_m = w_px / self.px_per_m
                    d_m = h_px / self.px_per_m
                    raw_obs.append({
                        "type": "box",
                        "center": [wx, wz],
                        "extent": [w_m, d_m]
                    })

        # ================= 算法调用 =================
        if self.show_algo and len(raw_pts) >= 2:
            try:
                # 传入动态的 world_range
                planner = PathPlanner(world_range=self.current_world_range, margin=self.algo_margin)
                planned_path_arr = planner.generate_path(
                    raw_pts, raw_obs, 
                    epsilon=self.algo_epsilon, 
                    smooth_factor=self.algo_smooth
                )
            except Exception as e:
                st.error(f"算法错误: {e}")

        # ================= 右侧预览 =================
        with col_output:
            st.markdown("### 👉 第二步：结果预览")
            # 传入动态 range 绘图
            fig = self._plot_preview_result(self.current_world_range, raw_pts, raw_obs, planned_path_arr)
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
                    item['height'] = getattr(self, 'obs_height', 2.0)
                    obstacles_json.append(item)
                
                traj_json = [[round(p[0], 2), round(p[1], 2)] for p in raw_pts]
                
                final_json = {
                    "project_name": self.proj_name,
                    # 保存当前的 map size，方便后端知道比例
                    "map_config": {"size": self.current_world_range},
                    "environment": {"obstacles": obstacles_json},
                    "trajectory": {
                        "type": "bezier_control_points",
                        "points": traj_json,
                    }
                }
                
                st.json(final_json)
                if st.button("💾 保存 Task JSON", type="primary", use_container_width=True,key=self._get_key("save_json_btn")):
                    self._save_json(final_json)

    def _save_json(self, data):
        try:
            with open(self.SAVE_PATH, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            st.success(f"✅ 保存成功: {self.SAVE_PATH}")
        except Exception as e:
            st.error(f"保存失败: {e}")