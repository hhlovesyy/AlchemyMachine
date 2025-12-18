# core/utils.py
import yaml
import os
import json

def load_yaml(path):
    if not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def save_yaml(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)

# 持久化状态管理 (替代原来的 alchemy_state.json)
STATE_FILE = "alchemy_state.json"

def save_persistent_state(key, value):
    """保存到硬盘，重启后还在"""
    try:
        data = {}
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                data = json.load(f)
        data[key] = value
        with open(STATE_FILE, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        print(f"State save failed: {e}")

def load_persistent_state(key, default=None):
    """从硬盘读取"""
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                data = json.load(f)
            return data.get(key, default)
    except:
        pass
    return default