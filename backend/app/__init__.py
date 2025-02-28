from flask import Flask
from flask_cors import CORS
from .config import Config
from .sql import db


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # 初始化 SQLAlchemy
    db.init_app(app)

    # 启用 CORS，允许所有来源跨域访问
    CORS(app)

    # 注册蓝图
    from .routes import bp as main_bp

    app.register_blueprint(main_bp)

    return app
