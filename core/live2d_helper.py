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
        return list(self.config.get("models", {}).keys())

    def get_message(self, state="idle"):
        dialogues = self.config.get("dialogues", {})
        msgs = dialogues.get(state, ["你好呀！"])
        return random.choice(msgs)

    def show(self, state="idle", model_name=None):
        models_dict = self.config.get("models", {})
        if not model_name or model_name not in models_dict:
            model_url = "https://fastly.jsdelivr.net/npm/live2d-widget-model-koharu@1.0.5/assets/koharu.model.json"
        else:
            model_url = models_dict[model_name]

        initial_message = self.get_message(state)
        idle_dialogues = self.config.get("dialogues", {}).get("idle", ["你好!"])
        js_dialogues_array = json.dumps(idle_dialogues)

        html_code = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <meta charset="utf-8">
        <style>
            /* 我们自定义的气泡，拥有最高权限 */
            .my-custom-tips {{
                position: fixed; bottom: 250px; left: 10px; width: 130px;
                padding: 8px; background: #fff; border: 2px solid #ffb6c1;
                border-radius: 8px; color: #333; font-size: 12px;
                font-family: "Microsoft YaHei", sans-serif;
                box-shadow: 0 4px 10px rgba(0,0,0,0.1);
                text-align: center; cursor: pointer; user-select: none;
                z-index: 10000;
                transition: transform 0.2s;
            }}
            .my-custom-tips:hover {{ transform: scale(1.05); }}
            .my-custom-tips::after {{
                content: ''; position: absolute; bottom: -10px; left: 40px;
                border-width: 10px 10px 0; border-style: solid;
                border-color: #ffb6c1 transparent;
            }}
        </style>
        <script src="https://fastly.jsdelivr.net/npm/live2d-widget@3.1.4/lib/L2Dwidget.min.js"></script>
        </head>
        <body>
            <!-- 我们自定义、可点击的气泡 -->
            <div class="my-custom-tips" id="waifu-tips">{initial_message}</div>
            
            <script>
                const idleDialogues = {js_dialogues_array};

                // 🔥 核心修复：使用最精简的配置，不添加任何 dialog 或 interaction 选项
                // 这样库会启用其默认的交互行为，即点击身体触发动画。
                L2Dwidget.init({{
                    "model": {{ "jsonPath": "{model_url}" }},
                    "display": {{ 
                        "position": "left", "width": 150, "height": 300,
                        "hOffset": 10, "vOffset": -20 
                    }},
                    "mobile": {{ "show": true }},
                    "react": {{ "opacityDefault": 1 }}
                }});

                // 我们自己的气泡逻辑，与 Live2D 库完全无关
                const tipsBox = document.getElementById('waifu-tips');
                if (tipsBox) {{
                    tipsBox.addEventListener('click', () => {{
                        const randomIndex = Math.floor(Math.random() * idleDialogues.length);
                        tipsBox.innerText = idleDialogues[randomIndex];
                    }});
                }}
            </script>
        </body>
        </html>
        """
        
        components.html(html_code, height=350, scrolling=False)