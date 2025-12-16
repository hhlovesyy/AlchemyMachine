# core/process_mgr.py
import subprocess
import os
import re
import datetime
import time # 引入time
from collections import deque

class ProcessManager:
    LOG_DIR = "logs"

    @staticmethod
    def _ensure_log_dir():
        if not os.path.exists(ProcessManager.LOG_DIR):
            os.makedirs(ProcessManager.LOG_DIR)

    @staticmethod
    def clean_ansi_codes(text):
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)

    @staticmethod
    def run_with_log(command, task_name, root_dir):
        ProcessManager._ensure_log_dir()
        time_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"{task_name}_{time_str}.log"
        log_path = os.path.join(ProcessManager.LOG_DIR, log_filename)
        abs_log_path = os.path.abspath(log_path)

        # === 核心修改：加上 python -u (Unbuffered) 确保日志不卡顿 ===
        # 如果 command 里包含 python，替换为 python -u
        if "python" in command and "python -u" not in command:
            command = command.replace("python", "python -u")

        full_cmd = (
            f"screen -dmS {task_name}_{time_str} bash -c "
            f"'cd {root_dir}; "
            f"echo \"=== Task Started: {time_str} ===\" > {abs_log_path}; "
            f"({command}) >> {abs_log_path} 2>&1; "
            f"echo \"\n=== Task Finished ===\" >> {abs_log_path}; "
            f"exec bash'"
        )

        try:
            subprocess.Popen(full_cmd, shell=True)
            # === 核心修改：稍微等一下文件创建 ===
            time.sleep(0.5) 
            return True, abs_log_path
        except Exception as e:
            return False, str(e)

    @staticmethod
    def read_log_tail(log_path, lines=100):
        """
        Python 原生实现的 Tail 功能，精准读取最后 N 行
        """
        if not log_path:
            return "⏳ 等待任务启动..."
        
        if not os.path.exists(log_path):
            return f"⏳ 日志文件初始化中...\nPath: {log_path}"

        try:
            # 如果文件是空的
            if os.path.getsize(log_path) == 0:
                return "📄 日志文件已创建，等待输出..."

            # 🔥 核心修改：使用 deque 固定长度队列读取，自动丢弃旧日志
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                # maxlen=lines 保证了内存里只保留最后 lines 行
                last_lines = deque(f, maxlen=lines)
                
            # 将列表拼接回字符串
            content = "".join(last_lines)
            
            # 简单的清洗（如果你不想看乱码）
            # clean_content = ProcessManager.clean_ansi_codes(content) 
            # 但为了保留终端颜色（如果用HTML渲染），建议保留原始内容，或者按需清洗
            # 这里我们为了HTML组件的兼容性，还是做一下基础清洗比较好，除非你想要彩色日志
            
            return content

        except Exception as e:
            return f"日志读取出错: {e}"