"""
User model. Supports three roles per the brief: Admin, Faculty, Student.
Tracks failed login attempts for basic brute-force lockout (a security
feature explicitly called out in the brief).
"""
import uuid
import enum
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


class UserRole(enum.Enum):
    ADMIN = "admin"
    FACULTY = "faculty"
    STUDENT = "student"


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.STUDENT)

    is_active = db.Column(db.Boolean, default=True)
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login_at = db.Column(db.DateTime, nullable=True)

    submissions = db.relationship("Submission", backref="student", lazy="dynamic")

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    def is_locked(self) -> bool:
        return bool(self.locked_until and self.locked_until > datetime.utcnow())

    def has_role(self, *roles: UserRole) -> bool:
        return self.role in roles

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "role": self.role.value,
            "is_active": self.is_active,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
        }
