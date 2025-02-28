from sqlalchemy import inspect
from .sql import db
from .models import create_model


def get_all_video():
    """
    查询数据库中所有以"video_"开头的表名，提取出视频id及对应的评论数量，并返回给前端。
    """
    try:
        inspector = inspect(db.engine)
        table_names = inspector.get_table_names()
        video_data = []
        for table in table_names:
            if table.startswith("video_"):
                # 提取视频id部分
                video_id = table[len("video_") :]
                # 通过动态模型获取评论表
                CommentModel = create_model(video_id)
                # 统计表中评论数量
                count = db.session.query(CommentModel).count()
                video_data.append({"video_id": video_id, "comment_count": count})
        return {"video_data": video_data}, 200
    except Exception as e:
        return {"error": str(e)}, 500
