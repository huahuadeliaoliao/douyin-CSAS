import requests
from flask import request


def login_handler():
    """
    处理登录逻辑，接收 JSON 数据中的 cookie，并将其转发给目标后端。
    返回一个二元组：(result, status_code)
    """
    data = request.get_json()
    if not data or "cookie" not in data:
        return {"error": "缺少 'cookie' 参数"}, 400

    cookie_value = data["cookie"]
    target_url = "http://douyin_api:5000/update_cookie"
    payload = {"cookie": cookie_value}
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(target_url, json=payload, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}, 500

    return response.json(), response.status_code
