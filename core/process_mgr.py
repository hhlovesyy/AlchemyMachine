# core/process_mgr.py
import subprocess
import os
import datetime
import time

class ProcessManager:
    LOG_DIR = "logs"

    @staticmethod
    def _ensure_log_dir():
        if not os.path.exists(ProcessManager.LOG_DIR):
            os.makedirs(ProcessManager.LOG_DIR)

    @staticmethod
    def run_with_log(command, task_name, root_dir):
        ProcessManager._ensure_log_dir()
        time_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"{task_name}_{time_str}.log"
        log_path = os.path.join(ProcessManager.LOG_DIR, log_filename)
        abs_log_path = os.path.abspath(log_path)

        # 1. 强制 Python 实时输出 (Unbuffered)
        if "python" in command and "python -u" not in command:
            real_cmd = command.replace("python", "python -u")
        else:
            real_cmd = command

        # === 🔥 核心黑科技 🔥 ===
        # 使用 script -q -c "command" /dev/null
        # 这会创建一个伪终端 (PTV/TTY)，强制 PyTorch Lightning 认为自己在交互式终端里
        # 从而吐出进度条和颜色代码。
        # 然后用 | tee 同时输出到屏幕和文件。
        
        # 注意：这里对引号进行了转义处理
        magic_cmd = f"script -q -c \"{real_cmd}\" /dev/null"

        full_cmd = (
            f"screen -dmS {task_name}_{time_str} bash -c "
            f"'cd {root_dir}; "
            f"echo \"--------------------------------\" | tee -a {abs_log_path}; "
            f"echo \"[CMD] {real_cmd}\" | tee -a {abs_log_path}; "
            f"echo \"--------------------------------\" | tee -a {abs_log_path}; "
            f"{magic_cmd} | tee -a {abs_log_path}; "  # <--- 这里的 magic_cmd 是关键
            f"echo \"\n=== Task Finished ===\" | tee -a {abs_log_path}; "
            f"exec bash'"
        )

        try:
            subprocess.Popen(full_cmd, shell=True)
            time.sleep(0.5) 
            return True, abs_log_path
        except Exception as e:
            return False, str(e)

    @staticmethod
    def read_log_tail(log_path, lines=200):
        if not log_path or not os.path.exists(log_path):
            return "⏳ 等待任务启动..."
        try:
            # 简单读取，交给前端去解析颜色
            cmd = f"tail -n {lines} {log_path}"
            return subprocess.check_output(cmd, shell=True).decode("utf-8", errors='ignore')
        except Exception as e:
            return f"日志读取出错: {e}"