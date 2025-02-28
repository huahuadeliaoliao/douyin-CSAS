import threading
import time
import json
import requests
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, current_app, stream_with_context
from sqlalchemy import inspect

from .config import Config
from .database import db, get_all_video
from .comments import fetch_replies_for_comment, create_model
from .video_info import get_video_info
from .login import login_handler
from .pipeline import generate_sentiment_results, infer_text_single

bp = Blueprint("main", __name__)

# ---------------------------
# 全局任务队列及锁
# ---------------------------
# 任务队列保存当前正在运行的任务，分别管理 fetch_comments 和 fetch_comments_replies
# 每个任务的结构示例：
# {
#    "video_id": <视频ID>,
#    "progress": { ... },
#    "status": "running",  # running, completed, cancelled, error
#    "cancel_event": threading.Event 对象,
#    "thread": <Thread对象>
# }
task_lock = threading.Lock()
tasks = {
    "fetch_comments": {},  # key 为 video_id
    "fetch_comments_replies": {},  # key 为 video_id
}


# ---------------------------
# 后台任务函数：抓取一级评论
# ---------------------------
def run_fetch_comments_task(video_id, task_info, app):
    with app.app_context():
        fetched_total = 0
        stored_total = 0
        cursor = 0
        external_url = f"{Config.DOUYIN_API_BASE_URI}/fetch_video_comments"
        CommentModel = create_model(video_id)
        with db.engine.begin() as conn:
            CommentModel.__table__.create(bind=conn, checkfirst=True)

        while True:
            # 检查是否收到取消信号
            if task_info["cancel_event"].is_set():
                task_info["status"] = "cancelled"
                break

            params = {"aweme_id": str(video_id), "cursor": cursor}
            try:
                # 设置合理的 timeout，防止一直阻塞
                ext_response = requests.get(external_url, params=params, timeout=5)
                ext_response.raise_for_status()
            except Exception as e:
                task_info["status"] = "error"
                task_info["error"] = str(e)
                break

            resp_json = ext_response.json()
            if (
                resp_json.get("code") != 200
                or resp_json.get("data", {}).get("status_code") != 0
            ):
                task_info["status"] = "error"
                task_info["error"] = resp_json
                break

            comments_list = resp_json.get("data", {}).get("comments", [])
            new_cursor = resp_json.get("data", {}).get("cursor")
            has_more = resp_json.get("data", {}).get("has_more", 0)
            if not comments_list:
                break

            fetched_total += len(comments_list)
            insert_data = []
            for item in comments_list:
                cid = item.get("cid")
                text = item.get("text")
                create_time = item.get("create_time")
                if cid and text and create_time:
                    dt = datetime.fromtimestamp(create_time, tz=timezone.utc)
                    reply_total = item.get("reply_comment_total", 0)
                    insert_data.append(
                        {
                            "cid": cid,
                            "text": text,
                            "create_time": dt,
                            "reply_comment_total": reply_total,
                        }
                    )

            if insert_data:
                cids_to_check = [d["cid"] for d in insert_data]
                existing_rows = CommentModel.query.filter(
                    CommentModel.cid.in_(cids_to_check)
                ).all()
                existing_cids = {row.cid for row in existing_rows}
                # 更新已有记录
                update_data = [d for d in insert_data if d["cid"] in existing_cids]
                if update_data:
                    try:
                        db.session.bulk_update_mappings(CommentModel, update_data)
                        db.session.commit()
                    except Exception as e:
                        db.session.rollback()
                        task_info["status"] = "error"
                        task_info["error"] = str(e)
                        break
                # 插入新记录
                final_data = [d for d in insert_data if d["cid"] not in existing_cids]
                if final_data:
                    try:
                        db.session.bulk_insert_mappings(CommentModel, final_data)
                        db.session.commit()
                        stored_total += len(final_data)
                    except Exception as e:
                        db.session.rollback()
                        task_info["status"] = "error"
                        task_info["error"] = str(e)
                        break

            # 更新任务进度信息
            task_info["progress"] = {"fetched": fetched_total, "stored": stored_total}

            if has_more == 1:
                cursor = new_cursor
            else:
                break

            # 用 cancel_event.wait 替代 time.sleep
            # 如果在等待期间 cancel_event 被 set，则立即退出
            if task_info["cancel_event"].wait(timeout=1):
                task_info["status"] = "cancelled"
                break

        if task_info.get("status") == "running":
            task_info["status"] = "completed"

        # 任务结束后，从全局任务队列中移除
        with task_lock:
            tasks["fetch_comments"].pop(video_id, None)


# ---------------------------
# 后台任务函数：抓取二级评论（回复）
# ---------------------------
def run_fetch_comments_replies_task(video_id, task_info, app):
    with app.app_context():
        CommentModel = create_model(video_id)
        inspector = inspect(db.engine)
        if CommentModel.__tablename__ not in inspector.get_table_names():
            task_info["status"] = "completed"
            with task_lock:
                tasks["fetch_comments_replies"].pop(video_id, None)
            return

        first_level_comments = CommentModel.query.filter(
            CommentModel.reply_comment_total > 0
        ).all()
        if not first_level_comments:
            task_info["status"] = "completed"
            with task_lock:
                tasks["fetch_comments_replies"].pop(video_id, None)
            return

        total_replies = 0
        processed_comments = 0
        for comment in first_level_comments:
            if task_info["cancel_event"].is_set():
                task_info["status"] = "cancelled"
                break

            replies_count = fetch_replies_for_comment(video_id, comment.cid)
            total_replies += replies_count
            processed_comments += 1

            task_info["progress"] = {
                "processed": processed_comments,
                "stored": total_replies,
            }
            if task_info["cancel_event"].wait(timeout=1):
                task_info["status"] = "cancelled"
                break

        if task_info.get("status") == "running":
            task_info["status"] = "completed"

        with task_lock:
            tasks["fetch_comments_replies"].pop(video_id, None)


# ---------------------------
# 普通接口（无需后台任务）
# ---------------------------
@bp.route("/login", methods=["POST"])
def login():
    result, status_code = login_handler()
    return jsonify(result), status_code


@bp.route("/all_store_videos", methods=["GET"])
def all_store_videos():
    result, status_code = get_all_video()
    return jsonify(result), status_code


@bp.route("/video_info", methods=["GET"])
def video_info():
    video_id = request.args.get("video_id")
    result, status_code = get_video_info(video_id)
    return jsonify(result), status_code


@bp.route("/sentiment_pipeline", methods=["GET"])
def sentiment_pipeline():
    video_id = request.args.get("video_id")
    start = request.args.get("start", default=0, type=int)
    if not video_id:
        return jsonify({"error": "缺少 video_id 参数"}), 400
    return current_app.response_class(
        stream_with_context(generate_sentiment_results(video_id, start_seq=start)),
        mimetype="application/x-ndjson",
    )


@bp.route("/infer_text", methods=["POST"])
def infer_text():
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "缺少文本参数"}), 400
    text = data["text"]
    result = infer_text_single(text)
    if result is None:
        return jsonify({"error": "推理失败"}), 429
    return jsonify({"result": result}), 200


# ---------------------------
# 非流式任务接口（分离任务创建与取消，保证原子性）
# ---------------------------
@bp.route("/fetch_comments", methods=["GET"])
def create_fetch_comments_task():
    """
    创建 fetch_comments 任务：
      - 如果相同 video_id 的任务已经存在，则返回错误
      - 全局同时允许最多 2 个 fetch_comments 任务
    """
    video_id = request.args.get("video_id")
    if not video_id:
        return jsonify({"error": "缺少 video_id 参数"}), 400

    with task_lock:
        if video_id in tasks["fetch_comments"]:
            return jsonify({"error": "相同 video_id 的任务已存在"}), 400

        if len(tasks["fetch_comments"]) >= 2:
            return jsonify(
                {"error": "当前任务数量已满，请先取消任务或者等待任务完成"}
            ), 400

        cancel_event = threading.Event()
        task_info = {
            "video_id": video_id,
            "progress": {},
            "status": "running",
            "cancel_event": cancel_event,
            "thread": None,
        }
        app_instance = current_app._get_current_object()
        thread = threading.Thread(
            target=run_fetch_comments_task, args=(video_id, task_info, app_instance)
        )
        task_info["thread"] = thread
        tasks["fetch_comments"][video_id] = task_info
        thread.start()

    return jsonify({"message": "任务已加入队列", "video_id": video_id}), 200


@bp.route("/cancel_fetch_comments", methods=["GET"])
def cancel_fetch_comments_task():
    """
    取消 fetch_comments 任务：
      - 使用 GET 方法，通过查询参数传入 video_id
      - 如果指定 video_id 对应的任务存在，则设置 cancel_event 标记
    """
    video_id = request.args.get("video_id")
    if not video_id:
        return jsonify({"error": "缺少 video_id 参数"}), 400

    with task_lock:
        if video_id not in tasks["fetch_comments"]:
            return jsonify({"error": "该 video_id 的任务不存在"}), 400
        tasks["fetch_comments"][video_id]["cancel_event"].set()

    return jsonify({"message": "任务取消请求已发送", "video_id": video_id}), 200


@bp.route("/fetch_comments_replies", methods=["GET"])
def fetch_comments_replies_endpoint():
    """
    非流式抓取二级评论：
      - 如果该 video_id 已有任务，则立即通过 cancel_event 通知取消
      - 全局同时允许最多 1 个 fetch_comments_replies 任务
    """
    video_id = request.args.get("video_id")
    if not video_id:
        return jsonify({"error": "缺少 video_id 参数"}), 400

    with task_lock:
        if video_id in tasks["fetch_comments_replies"]:
            tasks["fetch_comments_replies"][video_id]["cancel_event"].set()

        if len(tasks["fetch_comments_replies"]) >= 1:
            return jsonify(
                {"message": "当前任务数量已满，请先取消任务或者等待任务完成"}
            ), 200

        cancel_event = threading.Event()
        task_info = {
            "video_id": video_id,
            "progress": {},
            "status": "running",
            "cancel_event": cancel_event,
            "thread": None,
        }
        app_instance = current_app._get_current_object()
        thread = threading.Thread(
            target=run_fetch_comments_replies_task,
            args=(video_id, task_info, app_instance),
        )
        task_info["thread"] = thread
        tasks["fetch_comments_replies"][video_id] = task_info
        thread.start()

    return jsonify({"message": "任务已加入队列", "video_id": video_id}), 200


# ---------------------------
# 接口：查询任务进度（剔除不可序列化字段）
# ---------------------------
@bp.route("/task_progress", methods=["GET"])
def task_progress():
    video_id = request.args.get("video_id")
    result = {}
    with task_lock:
        if video_id:
            for task_type in tasks:
                if video_id in tasks[task_type]:
                    info = tasks[task_type][video_id].copy()
                    info.pop("thread", None)
                    info.pop("cancel_event", None)
                    result[task_type] = info
        else:
            for task_type, task_dict in tasks.items():
                result[task_type] = []
                for task_info in task_dict.values():
                    info = task_info.copy()
                    info.pop("thread", None)
                    info.pop("cancel_event", None)
                    result[task_type].append(info)
    return jsonify(result), 200
