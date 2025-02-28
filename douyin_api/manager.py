import subprocess
import os
import yaml
from flask import Flask, request, jsonify
import threading

app = Flask(__name__)

# 全局变量保存 start.py 的子进程对象和日志线程对象
start_process = None
log_thread = None

# 配置文件与 start.py 路径
CONFIG_PATH = "/app/crawlers/douyin/web/config.yaml"
START_SCRIPT = "start.py"


def log_output(proc):
    """实时读取并输出 start.py 的日志"""
    # 通过迭代 proc.stdout 的每一行进行实时输出
    for line in iter(proc.stdout.readline, ""):
        if not line:
            break
        # 日志前加上标识
        print("[douyin_api] " + line.rstrip())


def start_app():
    """启动 start.py 应用，并启动日志收集线程"""
    global start_process, log_thread
    print("启动 start.py 应用...")
    # 使用 text 模式，自动对输出进行解码
    start_process = subprocess.Popen(
        ["python3", START_SCRIPT],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
        text=True,
    )
    # 启动线程实时读取子进程日志
    log_thread = threading.Thread(target=log_output, args=(start_process,))
    log_thread.daemon = True
    log_thread.start()
    print(f"应用已启动，PID: {start_process.pid}")


def stop_app():
    """停止正在运行的 start.py 应用，并关闭日志线程"""
    global start_process, log_thread
    if start_process is not None:
        print("停止正在运行的 start.py 应用...")
        start_process.terminate()
        try:
            start_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            start_process.kill()
        # 等待日志线程结束
        if log_thread is not None:
            log_thread.join(timeout=1)
        start_process = None
        log_thread = None
    else:
        print("没有正在运行的应用。")


@app.route("/update_cookie", methods=["POST"])
def update_cookie():
    """
    接收 POST 请求，JSON 格式需要包含 key: "cookie"
    例如：{"cookie": "新的 Cookie 值"}
    """
    new_cookie = request.json.get("cookie")
    if not new_cookie:
        return jsonify({"error": "请求中必须包含 cookie 字段"}), 400

    # 检查配置文件是否存在
    if not os.path.exists(CONFIG_PATH):
        return jsonify({"error": f"配置文件 {CONFIG_PATH} 不存在"}), 500

    # 读取 YAML 配置文件
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except Exception as e:
        return jsonify({"error": f"读取配置文件失败: {str(e)}"}), 500

    # 修改 Cookie 值
    try:
        config["TokenManager"]["douyin"]["headers"]["Cookie"] = new_cookie
    except KeyError as e:
        return jsonify({"error": f"配置文件格式错误，缺少键: {str(e)}"}), 500

    # 写回 YAML 文件
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.dump(config, f, allow_unicode=True)
    except Exception as e:
        return jsonify({"error": f"写入配置文件失败: {str(e)}"}), 500

    # 重启 start.py 应用
    stop_app()
    start_app()

    return jsonify({"message": "Cookie 已更新，应用已重启"}), 200


if __name__ == "__main__":
    # 启动 start.py 应用
    start_app()
    # 启动 Flask 服务，监听所有网卡的 5000 端口
    app.run(host="0.0.0.0", port=5000)
