"""
Secure Online Examination System — Application Factory
Project 6: Secure Online Examination System with Proctoring Logs

Backend owner: Jaskirat
"""
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()


def create_app(config_name=None):
    app = Flask(__name__)

    config_name = config_name or os.getenv("FLASK_ENV", "development")
    from config import config_by_name
    app.config.from_object(config_by_name[config_name])

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # Teammate's frontend runs on a different origin during development
    CORS(app, resources={r"/api/*": {"origins": app.config.get("CORS_ORIGINS", "*")}},
         supports_credentials=True)

    from app.routes.auth_routes import auth_bp
    from app.routes.exam_routes import exam_bp
    from app.routes.question_routes import question_bp
    from app.routes.admin_routes import admin_bp
    from app.routes.proctoring_routes import proctoring_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(exam_bp, url_prefix="/api/exams")
    app.register_blueprint(question_bp, url_prefix="/api/questions")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(proctoring_bp, url_prefix="/api/proctoring")

    from app.utils.error_handlers import register_error_handlers
    register_error_handlers(app)

    @app.route("/api/health", methods=["GET"])
    def health():
        return {"status": "ok"}, 200

    return app
