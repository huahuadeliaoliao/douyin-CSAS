import requests
import json
import time
import concurrent.futures
from datetime import datetime, timezone
from flask import current_app, request
from sqlalchemy import inspect

from .models import create_model
from .sql import db
from .config import Config


def fetch_and_store_comments(video_id):
    """
    根据 video_id 分批次抓取评论，并将其存入以 video_id 命名的表中（仅存储一级评论）。
    使用接口返回的 reply_comment_total 字段来记录每条评论的回复数量。
    如果数据库中已存在相同 cid 的记录，则更新该记录。
    """
    if not video_id:
        return {"error": "缺少视频ID参数"}, 400

    try:
        int(video_id)
    except ValueError:
        pass

    CommentModel = create_model(video_id)

    with db.engine.begin() as conn:
        CommentModel.__table__.create(bind=conn, checkfirst=True)

    stored_comments = 0
    cursor = 0
    external_url = f"{Config.DOUYIN_API_BASE_URI}/fetch_video_comments"

    while True:
        params = {
            "aweme_id": str(video_id),
            "cursor": cursor,
        }

        try:
            ext_response = requests.get(external_url, params=params)
            ext_response.raise_for_status()
        except requests.RequestException as e:
            return {"error": "获取评论数据失败", "details": str(e)}, 500

        resp_json = ext_response.json()
        if (
            resp_json.get("code") != 200
            or resp_json.get("data", {}).get("status_code") != 0
        ):
            return {"error": "外部接口返回错误", "data": resp_json}, 500

        comments_list = resp_json.get("data", {}).get("comments", [])
        new_cursor = resp_json.get("data", {}).get("cursor")
        has_more = resp_json.get("data", {}).get("has_more", 0)
        if not comments_list:
            break

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
                    return {"error": "更新评论数据失败", "details": str(e)}, 500
            # 插入新记录
            final_data = [d for d in insert_data if d["cid"] not in existing_cids]
            if final_data:
                try:
                    db.session.bulk_insert_mappings(CommentModel, final_data)
                    db.session.commit()
                    stored_comments += len(final_data)
                except Exception as e:
                    db.session.rollback()
                    return {"error": "存储评论数据失败", "details": str(e)}, 500

        # 根据 has_more 判断是否继续抓取
        if has_more == 1:
            cursor = new_cursor
        else:
            break

        time.sleep(3)

    if stored_comments == 0:
        return {"message": "没有存入新评论"}, 200
    else:
        return {"message": f"成功存储 {stored_comments} 条评论"}, 200


def fetch_replies_for_comment(video_id, first_comment_cid):
    """
    辅助函数：获取某个一级评论的所有二级评论，并存入数据库（不再存储评论级别）。
    对于二级评论，reply_comment_total 默认设为 0。
    """
    CommentModel = create_model(video_id)
    cursor = 0
    total_replies = 0
    external_url = f"{Config.DOUYIN_API_BASE_URI}/fetch_video_comment_replies"

    while True:
        params = {
            "item_id": str(video_id),
            "comment_id": first_comment_cid,
            "cursor": cursor,
        }
        try:
            ext_response = requests.get(external_url, params=params)
            ext_response.raise_for_status()
        except requests.RequestException as e:
            print(f"获取评论 {first_comment_cid} 回复时出错：{e}")
            break

        resp_json = ext_response.json()
        if (
            resp_json.get("code") != 200
            or resp_json.get("data", {}).get("status_code") != 0
        ):
            print(f"评论 {first_comment_cid} 回复接口返回错误：{resp_json}")
            break

        replies_list = resp_json.get("data", {}).get("comments", [])
        new_cursor = resp_json.get("data", {}).get("cursor")
        has_more = resp_json.get("data", {}).get("has_more", 0)
        if not replies_list:
            break

        insert_data = []
        for item in replies_list:
            cid = item.get("cid")
            text = item.get("text")
            create_time = item.get("create_time")
            if cid and text and create_time:
                dt = datetime.fromtimestamp(create_time, tz=timezone.utc)
                # 对于二级评论，不存储级别，reply_comment_total 默认为 0
                insert_data.append(
                    {
                        "cid": cid,
                        "text": text,
                        "create_time": dt,
                        "reply_comment_total": 0,
                    }
                )

        if insert_data:
            cids_to_check = [d["cid"] for d in insert_data]
            existing_rows = CommentModel.query.filter(
                CommentModel.cid.in_(cids_to_check)
            ).all()
            existing_cids = {row.cid for row in existing_rows}
            # 更新已有的二级评论（如果需要更新信息）
            update_data = [d for d in insert_data if d["cid"] in existing_cids]
            if update_data:
                try:
                    db.session.bulk_update_mappings(CommentModel, update_data)
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    print(f"更新评论 {first_comment_cid} 回复时出错：{e}")
            # 插入新记录
            final_data = [d for d in insert_data if d["cid"] not in existing_cids]
            if final_data:
                try:
                    db.session.bulk_insert_mappings(CommentModel, final_data)
                    db.session.commit()
                    total_replies += len(final_data)
                except Exception as e:
                    db.session.rollback()
                    print(f"存储评论 {first_comment_cid} 回复时出错：{e}")

        if has_more == 1:
            cursor = new_cursor
        else:
            break

        time.sleep(3)
    return total_replies


def fetch_replies_with_context(video_id, comment_cid, app):
    """
    包装函数：在应用上下文中执行获取回复的操作。
    """
    with app.app_context():
        return fetch_replies_for_comment(video_id, comment_cid)


def fetch_and_store_comments_replies(video_id):
    """
    根据视频ID获取该视频所有一级评论的二级评论，并将二级评论存入数据库。
    该函数首先查询数据库中 reply_comment_total 大于 0 的评论，
    只有这些评论才会触发获取回复的操作。
    """
    if not video_id:
        return {"error": "缺少视频ID参数"}, 400

    CommentModel = create_model(video_id)
    inspector = inspect(db.engine)
    if CommentModel.__tablename__ not in inspector.get_table_names():
        return {"message": "该视频尚未获取任何评论"}, 200

    first_level_comments = CommentModel.query.filter(
        CommentModel.reply_comment_total > 0
    ).all()
    if not first_level_comments:
        return {"message": "该视频尚未获取任何有回复的评论"}, 200

    total_replies = 0
    app = current_app._get_current_object()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = []
        for comment in first_level_comments:
            futures.append(
                executor.submit(fetch_replies_with_context, video_id, comment.cid, app)
            )
        for future in concurrent.futures.as_completed(futures):
            total_replies += future.result()

    return {"message": f"成功存储 {total_replies} 条二级评论"}, 200


#############################################
# 以下是流式返回进度的生成器函数
#############################################


def generate_fetch_comments(video_id):
    """
    流式获取视频一级评论：
      - 定期返回已抓取的评论总数和存入数据库的新评论数
      - 如果客户端断开连接则提前退出
    """
    if not video_id:
        yield json.dumps({"error": "缺少视频ID参数"})
        return

    try:
        int(video_id)
    except ValueError:
        pass

    CommentModel = create_model(video_id)
    with db.engine.begin() as conn:
        CommentModel.__table__.create(bind=conn, checkfirst=True)

    fetched_total = 0
    stored_total = 0
    cursor = 0
    external_url = f"{Config.DOUYIN_API_BASE_URI}/fetch_video_comments"

    while True:
        params = {
            "aweme_id": str(video_id),
            "cursor": cursor,
        }
        try:
            ext_response = requests.get(external_url, params=params)
            ext_response.raise_for_status()
        except requests.RequestException as e:
            yield json.dumps({"error": "获取评论数据失败", "details": str(e)})
            return

        resp_json = ext_response.json()
        if (
            resp_json.get("code") != 200
            or resp_json.get("data", {}).get("status_code") != 0
        ):
            yield json.dumps({"error": "外部接口返回错误", "data": resp_json})
            return

        comments_list = resp_json.get("data", {}).get("comments", [])
        new_cursor = resp_json.get("data", {}).get("cursor")
        has_more = resp_json.get("data", {}).get("has_more", 0)
        if not comments_list:
            # 无新数据时返回最终进度
            yield json.dumps({"fetched": fetched_total, "stored": stored_total})
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
                    yield json.dumps({"error": "更新评论数据失败", "details": str(e)})
                    return
            # 插入新记录
            final_data = [d for d in insert_data if d["cid"] not in existing_cids]
            if final_data:
                try:
                    db.session.bulk_insert_mappings(CommentModel, final_data)
                    db.session.commit()
                    stored_total += len(final_data)
                except Exception as e:
                    db.session.rollback()
                    yield json.dumps({"error": "存储评论数据失败", "details": str(e)})
                    return

        # 定期返回进度（仅返回抓取的评论数量和存入数据库的新评论数量）
        yield json.dumps({"fetched": fetched_total, "stored": stored_total})

        if has_more == 1:
            cursor = new_cursor
        else:
            break

        time.sleep(1)
        # 检查客户端是否断开连接
        if request.environ.get("wsgi.input") and getattr(
            request.environ.get("wsgi.input"), "closed", False
        ):
            break

    yield json.dumps({"fetched": fetched_total, "stored": stored_total})


def generate_fetch_comments_replies(video_id):
    """
    流式获取视频一级评论对应的二级评论：
      - 定期返回已处理的一级评论数量（即已抓取其回复的评论数）和存入数据库的新回复数
      - 如果客户端断开连接则提前退出
    """
    if not video_id:
        yield json.dumps({"error": "缺少视频ID参数"})
        return

    CommentModel = create_model(video_id)
    inspector = inspect(db.engine)
    if CommentModel.__tablename__ not in inspector.get_table_names():
        yield json.dumps(
            {"fetched": 0, "stored": 0, "message": "该视频尚未获取任何评论"}
        )
        return

    first_level_comments = CommentModel.query.filter(
        CommentModel.reply_comment_total > 0
    ).all()
    if not first_level_comments:
        yield json.dumps(
            {"fetched": 0, "stored": 0, "message": "该视频尚未获取任何有回复的评论"}
        )
        return

    total_replies = 0
    processed_comments = 0
    app = current_app._get_current_object()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(
                fetch_replies_with_context, video_id, comment.cid, app
            ): comment.cid
            for comment in first_level_comments
        }
        for future in concurrent.futures.as_completed(futures):
            try:
                replies_count = future.result()
            except Exception:
                replies_count = 0
            total_replies += replies_count
            processed_comments += 1
            yield json.dumps({"fetched": processed_comments, "stored": total_replies})
            # 检查客户端是否断开连接
            if request.environ.get("wsgi.input") and getattr(
                request.environ.get("wsgi.input"), "closed", False
            ):
                break

    yield json.dumps({"fetched": processed_comments, "stored": total_replies})
