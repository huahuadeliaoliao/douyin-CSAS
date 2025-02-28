import json
from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks
from .models import create_model
from .sql import db
from sqlalchemy import inspect
from flask import request

# 定义全局默认批次大小
DEFAULT_BATCH_SIZE = 20

# 在模块加载时预先初始化情绪分析模型
model_dir = "/app/bert"
semantic_cls = pipeline(
    Tasks.text_classification,
    model_revision="v1.0.0",
    model=model_dir,
)


def client_disconnected():
    """
    检查客户端是否已断开连接
    """
    inp = request.environ.get("wsgi.input")
    return inp and getattr(inp, "closed", False)


def analyze_comments_sentiment(comment_texts, batch_size=DEFAULT_BATCH_SIZE):
    """
    对多条评论文本进行情绪分析，返回每条文本对应的预测情绪标签列表。
    通过一次调用 pipeline 的批量推理来提升效率。
    """
    results = semantic_cls(input=comment_texts, batch_size=batch_size)
    predicted_labels = []
    for result in results:
        scores = result.get("scores", [])
        labels = result.get("labels", [])
        if not scores or not labels:
            predicted_labels.append(None)
        else:
            max_index = scores.index(max(scores))
            predicted_labels.append(labels[max_index])
    return predicted_labels


def generate_sentiment_results(video_id, start_seq=0, batch_size=DEFAULT_BATCH_SIZE):
    """
    生成器：从数据库中批量读取评论，按批量进行情绪分析，并以 JSON 字符串的形式 yield 给前端。
    可通过 start_seq 参数指定从某个序号开始处理数据。
    在处理过程中，会检查客户端是否断开连接，如果断开，则提前终止任务。
    """
    CommentModel = create_model(video_id)
    insp = inspect(db.engine)
    if CommentModel.__tablename__ not in insp.get_table_names():
        yield json.dumps({"error": "该视频没有评论数据"}) + "\n"
        return

    # 通过过滤 seq 字段实现分页
    query = (
        CommentModel.query.filter(CommentModel.seq >= start_seq)
        .order_by(CommentModel.seq)
        .yield_per(batch_size)
    )

    comments_batch = []
    comment_objs = []

    for comment in query:
        if client_disconnected():
            return
        comments_batch.append(comment.text)
        comment_objs.append(comment)
        if len(comments_batch) == batch_size:
            predicted_emotions = analyze_comments_sentiment(
                comments_batch, batch_size=batch_size
            )
            for com_obj, emotion in zip(comment_objs, predicted_emotions):
                result_dict = {
                    "seq": com_obj.seq,
                    "cid": com_obj.cid,
                    "text": com_obj.text,
                    "create_time": com_obj.create_time.isoformat()
                    if com_obj.create_time
                    else "",
                    "reply_comment_total": com_obj.reply_comment_total,
                    "predicted_emotion": emotion,
                }
                if client_disconnected():
                    return
                yield json.dumps(result_dict) + "\n"
            comments_batch = []
            comment_objs = []

    if comments_batch:
        if client_disconnected():
            return
        predicted_emotions = analyze_comments_sentiment(
            comments_batch, batch_size=len(comments_batch)
        )
        for com_obj, emotion in zip(comment_objs, predicted_emotions):
            result_dict = {
                "seq": com_obj.seq,
                "cid": com_obj.cid,
                "text": com_obj.text,
                "create_time": com_obj.create_time.isoformat()
                if com_obj.create_time
                else "",
                "reply_comment_total": com_obj.reply_comment_total,
                "predicted_emotion": emotion,
            }
            if client_disconnected():
                return
            yield json.dumps(result_dict) + "\n"


def infer_text_single(text):
    """
    对单条文本进行情绪推理，返回所有预测的情绪标签及其对应的置信度。
    使用全局初始化的 semantic_cls pipeline 实例进行推理。
    """
    results = semantic_cls(input=[text], batch_size=1)
    if not results:
        return None

    result = results[0]
    scores = result.get("scores", [])
    labels = result.get("labels", [])
    if not scores or not labels:
        return None

    all_confidences = {label: score for label, score in zip(labels, scores)}
    return all_confidences
