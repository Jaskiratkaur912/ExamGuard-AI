"""
RBAC decorator — guards routes by required role(s). Also exposes the current
user via flask.g for convenience inside route handlers.
"""
from functools import wraps
from flask import jsonify, g
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from app.models import User


def roles_required(*allowed_roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            user = User.query.get(user_id)

            if user is None or not user.is_active:
                return jsonify({"error": "Unauthorized"}), 401

            if user.role not in allowed_roles:
                return jsonify({"error": "Forbidden: insufficient role"}), 403

            g.current_user = user
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def any_authenticated(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if user is None or not user.is_active:
            return jsonify({"error": "Unauthorized"}), 401

        g.current_user = user
        return fn(*args, **kwargs)
    return wrapper
