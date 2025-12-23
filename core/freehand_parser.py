import re
import numpy as np

class FreehandParser:
    def __init__(self, center_pixel, px_per_m):
        """
        :param center_pixel: 画布中心点像素值 (例如 300)
        :param px_per_m: 比例尺 (像素/米)
        """
        self.center = center_pixel
        self.scale = px_per_m

    def parse_svg_path(self, svg_path_data, sample_step=5):
        """
        解析 SVG 路径数据，并转换为物理坐标
        :param svg_path_data:可能是字符串 "M 10 10..." 也可能是列表 [['M',10,10]...]
        :return: np.array [[x, y], ...] (物理坐标)
        """
        if not svg_path_data:
            return None

        # === 🔥 核心修复：强制转为字符串 🔥 ===
        # 无论它给的是 String 还是 List，强转字符串后，
        # 正则表达式都能从中把数字提取出来。
        path_str = str(svg_path_data)

        # 1. 使用正则提取所有坐标数值
        # 匹配整数或小数
        tokens = re.findall(r"[-+]?\d*\.\d+|[-+]?\d+", path_str)
        
        # 转为浮点数列表
        try:
            coords = [float(t) for t in tokens]
        except:
            return None

        # 2. 提取 (x, y) 对
        # SVG path 可能包含控制点，或者 M/L/Q 指令
        # 简单起见，我们提取所有的数字对作为轨迹点
        pixel_points = []
        for i in range(0, len(coords), 2):
            if i + 1 < len(coords):
                pixel_points.append([coords[i], coords[i+1]])
        
        if not pixel_points:
            return None

        # 3. 坐标转换 (Pixel -> World) & 降采样
        world_points = []
        for i, (px, py) in enumerate(pixel_points):
            # 简单的降采样：每隔 sample_step 个点取一个
            # 防止手绘产生的点过于密集（几千个点）
            if i % sample_step == 0: 
                wx = (px - self.center) / self.scale
                wz = -(py - self.center) / self.scale # Y轴反转，保持上北下南
                world_points.append([wx, wz])
        
        # 确保至少有点
        if len(world_points) == 0:
            return None
            
        return np.array(world_points)