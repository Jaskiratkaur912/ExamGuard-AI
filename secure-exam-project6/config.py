"""
Configuration — values pulled from environment variables. Never hardcode
secrets or DB credentials here.
"""
import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))


class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-env")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-in-env")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=2)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)

    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")

    # Exam engine
    EXAM_AUTO_SUBMIT_GRACE_SECONDS = 30
    MAX_LOGIN_ATTEMPTS_BEFORE_LOCK = 5
    ACCOUNT_LOCK_MINUTES = 15


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/secure_exam_p6_dev",
    )


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/secure_exam_p6_test",
    )
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)


class ProductionConfig(BaseConfig):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
