import requests
import datetime
from datetime import timezone
from .config import Config


def get_video_info(video_id):
    """
    根据视频ID获取视频信息，包括基本属性和统计数据。

    参数:
        video_id (str): 视频的唯一标识符（aweme_id）
    返回:
        tuple: (result_dict, status_code)
    """
    if not video_id:
        return {"error": "video_id is required"}, 400

    external_url = f"{Config.DOUYIN_API_BASE_URI}/fetch_one_video"
    params = {"aweme_id": video_id}
    try:
        response = requests.get(external_url, params=params)
        if response.status_code != 200:
            return {
                "error": "Failed to fetch video info from douyin api"
            }, response.status_code

        data = response.json()

        detail = data.get("data", {}).get("aweme_detail", {})

        video_id = detail.get("aweme_id", video_id)
        description = detail.get("desc", "")
        create_time_ts = detail.get("create_time", 0)
        try:
            dt = datetime.fromtimestamp(create_time_ts, tz=timezone.utc)
            create_time_iso = dt.isoformat()
        except Exception:
            create_time_iso = ""

        # 处理时长：如果 duration 大于 1000，则认为单位为毫秒，否则为秒
        duration_raw = detail.get("duration", 0)
        if duration_raw > 1000:
            duration_sec = round(duration_raw / 1000)
        else:
            duration_sec = duration_raw

        stats_raw = detail.get("statistics", {})
        stats = {
            "play_count": stats_raw.get("play_count", 0),
            "like_count": stats_raw.get("digg_count", 0),
            "comment_count": stats_raw.get("comment_count", 0),
            "share_count": stats_raw.get("share_count", 0),
            "favorite_count": stats_raw.get("collect_count", 0),
        }

        video_info = detail.get("video", {})
        cover_info = video_info.get("cover", {})
        cover_url_list = cover_info.get("url_list", [])
        # 如果有数据，就取第一个作为封面地址，否则为空字符串
        cover_url = cover_url_list[0] if cover_url_list else ""

        result = {
            "video_id": video_id,
            "description": description,
            "create_time": create_time_iso,
            "duration": duration_sec,
            "cover_url": cover_url,
            "stats": stats,
        }
        return result, 200

    except Exception as e:
        return {"error": str(e)}, 500
