from sqlalchemy import Column, String, Text, DateTime, Integer, Sequence, Index
from .sql import db

# 定义一个全局缓存字典
_model_cache = {}


def create_model(video_id):
    """
    针对每个 video_id 动态创建一个评论表模型，并且只创建一次。
    新增自增序号字段 seq，并为 seq 和 create_time 建立索引，
    以便后续实现高效的键集分页查询（例如：通过序号或时间戳查询）。
    """
    if video_id in _model_cache:
        return _model_cache[video_id]

    table_name = f"video_{video_id}"
    class_name = f"DynamicComment_{video_id}"
    seq_name = f"seq_{table_name}"
    seq = Sequence(seq_name, start=1, increment=1)

    model = type(
        class_name,
        (db.Model,),
        {
            "__tablename__": table_name,
            "__table_args__": (
                Index(f"idx_seq_{video_id}", "seq"),
                Index(f"idx_create_time_{video_id}", "create_time"),
                {"extend_existing": True},
            ),
            "seq": Column(
                Integer, seq, server_default=seq.next_value(), nullable=False
            ),
            "cid": Column(String(50), primary_key=True),
            "text": Column(Text, nullable=False),
            "create_time": Column(DateTime(timezone=True), nullable=False),
            "reply_comment_total": Column(Integer, default=0, nullable=False),
            "__repr__": lambda self: f"<Comment {self.cid}>",
        },
    )

    _model_cache[video_id] = model
    return model
