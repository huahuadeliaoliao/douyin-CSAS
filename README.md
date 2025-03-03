<p align="center">
  <img src="frontend/public/emotique.webp" width="200" height="200" alt="Emotique Logo">
</p>

<h1 align="center">Emotique</h1>

> :warning: **警告：本项目仅用于个人学习，请勿用于其他任何用途，后果自负！**

---

## 功能简介

Emotique 是一个基于通义实验室开源的[StructBERT情绪分类-中文-七分类-large](https://www.modelscope.cn/models/iic/nlp_structbert_emotion-classification_chinese-large)模型的评论情绪分析系统，拥有两大核心功能：

- **实时同步评论**  
  只需导入抖音视频 ID，即可同步视频评论数据。
- **评论情绪可视化**  
  通过直观的图表展示评论情绪趋势，帮助用户快速了解情绪分布。

---

## 项目组成

- [Douyin_TikTok_Download_API](https://github.com/Evil0ctal/Douyin_TikTok_Download_API)
- [ModelScope](https://www.modelscope.cn/home)
- Flask
- Postgres
- Vue
- Tailwind CSS

---

## 系统部署

本项目使用 Docker Compose 进行部署，默认使用CPU进行模型推理的镜像，支持切换为 NVIDIA GPU 镜像。

如果需要启用 NVIDIA GPU，请先安装 NVIDIA Docker 支持，然后按照 docker-compose.yml 中的注释进行操作。

> **注意：**
>
> - Dockerfile.cuda 默认使用 CUDA 12.1 版本。如果需要使用 CUDA 11.8 版本，请参考 backend 文件夹中的 Dockerfile.cuda 文件中的说明进行切换。

部署命令如下

```bash
# 拉取源码
git clone https://github.com/huahuadeliaoliao/douyin-CSAS.git && cd douyin-CSAS

# 下载 StructBERT情绪分类-中文-七分类-large 模型以及配置文件
mkdir -p backend/bert && \
curl -L -o backend/bert/pytorch_model.bin "https://www.modelscope.cn/models/iic/nlp_structbert_emotion-classification_chinese-large/file/view/master?fileName=pytorch_model.bin&status=2" && \
curl -L -o backend/bert/config.json "https://www.modelscope.cn/models/iic/nlp_structbert_emotion-classification_chinese-large/file/view/master?fileName=config.json&status=1" && \
curl -L -o backend/bert/configuration.json "https://www.modelscope.cn/models/iic/nlp_structbert_emotion-classification_chinese-large/file/view/master?fileName=configuration.json&status=1" && \
curl -L -o backend/bert/vocab.txt "https://www.modelscope.cn/models/iic/nlp_structbert_emotion-classification_chinese-large/file/view/master?fileName=vocab.txt&status=1"

# 使用docker compose在后台启动系统
docker compose up --build -d
```

---

## 界面功能
