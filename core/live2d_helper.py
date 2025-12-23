import streamlit as st
import streamlit.components.v1 as components
import json
import os
import random

class Live2DHelper:
    def __init__(self):
        self.config_path = "configs/live2d_config.json"
        self.config = self._load_config()

    def _load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def get_available_models(self):
        """返回模型名称列表供下拉框使用"""
        return list(self.config.get("models", {}).keys())

    def get_message(self, state="idle"):
        """根据状态获取台词"""
        dialogues = self.config.get("dialogues", {})
        msgs = dialogues.get(state, ["你好呀！"])
        return random.choice(msgs)

    def show(self, state="idle", model_name=None):
        # 1. 确定模型 URL
        models_dict = self.config.get("models", {})
        # 如果没选，默认用第一个
        if not model_name or model_name not in models_dict:
            # 默认 fallback
            model_url = "https://fastly.jsdelivr.net/npm/live2d-widget-model-koharu@1.0.5/assets/koharu.model.json"
        else:
            model_url = models_dict[model_name]

        # 2. 获取当前状态的台词
        message = self.get_message(state)
        
        # 3. HTML 构造 (增强版)
        html_code = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <meta charset="utf-8">
        <style>
            body {{ margin: 0; padding: 0; overflow: hidden; }}
            
            /* --- 修改点 1: 气泡样式调整 --- */
            .tips {{
                position: fixed;
                bottom: 250px;       /* 稍微降低一点，适应变矮的小人 */
                left: 250px;          /* 🔥 改成 left，让气泡靠左显示 */
                width: 130px;        /* 稍微变窄一点，适应侧边栏 */
                padding: 8px;
                background: #fff;
                border: 2px solid #ffb6c1;
                border-radius: 8px;
                color: #333;
                font-size: 20px;     /* 字体改小一点点 */
                font-family: "Microsoft YaHei", sans-serif;
                box-shadow: 0 4px 10px rgba(0,0,0,0.1);
                pointer-events: auto;
                text-align: center;
                opacity: 0;
                animation: popIn 0.5s forwards;
            }}
            
            /* 气泡小尾巴方向也改一下 */
            .tips::after {{
                content: '';
                position: absolute;
                bottom: -10px;
                left: 100px;          /* 🔥 尾巴也移到左边 */
                border-width: 10px 10px 0;
                border-style: solid;
                border-color: #ffb6c1 transparent;
            }}
            
            @keyframes popIn {{
                0% {{ opacity: 0; transform: translateY(10px); }}
                100% {{ opacity: 1; transform: translateY(0); }}
            }}
        </style>
        <script src="https://fastly.jsdelivr.net/npm/live2d-widget@3.1.4/lib/L2Dwidget.min.js"></script>
        </head>
        <body>
            <div class="tips" id="waifu-tips">{message}</div>
            
            <script>
                L2Dwidget.init({{
                    "model": {{ 
                        "jsonPath": "{model_url}", 
                        "scale": 1 
                    }},
                    "display": {{ 
                        "position": "left",   // 🔥 修改点 2: 改为靠左对齐
                        "width": 250,         // 🔥 修改点 3: 宽度变小 (250 -> 150)
                        "height": 500,        // 🔥 修改点 3: 高度变小 (500 -> 300)
                        "hOffset": 10,        // 左边距 10px
                        "vOffset": -20        // 底部微调
                    }},
                    "mobile": {{ "show": true, "scale": 0.5 }},
                    "react": {{ "opacityDefault": 1, "opacityOnHover": 1 }}
                }});

                setInterval(() => {{
                    const tips = document.getElementById('waifu-tips');
                    tips.style.opacity = (tips.style.opacity == '0' ? '1' : '0');
                }}, 8000);
            </script>
        </body>
        </html>
        """
        
        # 🔥 关键修改：高度给足 400，宽度自适应
        # 放在 Sidebar 里时，这个宽度刚好占满 Sidebar 底部
        components.html(html_code, height=400, scrolling=False)