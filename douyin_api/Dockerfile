FROM evil0ctal/douyin_tiktok_download_api:b438d69

COPY manager.py /app/manager.py

RUN pip install Flask

WORKDIR /app

CMD ["python3", "manager.py"]
