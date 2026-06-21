"""
Authentication routes: register, login, token refresh.
Implements account lockout after repeated failed attempts and records
every login attempt (success or failure) to LoginHistory.
"""
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app, g
from flask_jwt_extended import (
    create_access_token, create_refresh_token, jwt_required,
    get_jwt_identity, get_jwt,
)
from app import db
from app.models import User, UserRole
from app.utils.validation import (
    ValidationError, require_fields, validate_email,
    validate_password_strength, sanitize_text,
)
from app.utils.rbac import any_authenticated
from app.services.audit_service import log_activity, log_login_attempt

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    require_fields(data, ["full_name", "email", "password"])

    full_name = sanitize_text(data["full_name"], max_length=120)
    email = validate_email(data["email"])
    password = validate_password_strength(data["password"])

    if User.query.filter_by(email=email).first():
        raise ValidationError("Email already registered", field="email")

    role_value = data.get("role", "student")
    try:
        role = UserRole(role_value)
    except ValueError:
        raise ValidationError("Invalid role", field="role")

    # Self-registration limited to Student. Faculty/Admin accounts must be
    # provisioned by an existing Admin via /api/admin/users.
    if role != UserRole.STUDENT:
        return jsonify({"error": "Only student self-registration is allowed"}), 403

    user = User(full_name=full_name, email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    log_activity(user.id, "user_registered", resource_type="user", resource_id=user.id)

    return jsonify(user.to_dict()), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first()

    if user and user.is_locked():
        log_login_attempt(user.id, email, success=False, failure_reason="account_locked")
        return jsonify({"error": "Account temporarily locked due to repeated failed attempts"}), 403

    if not user or not user.check_password(password):
        if user:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= current_app.config["MAX_LOGIN_ATTEMPTS_BEFORE_LOCK"]:
                user.locked_until = datetime.utcnow() + timedelta(
                    minutes=current_app.config["ACCOUNT_LOCK_MINUTES"]
                )
            db.session.commit()
        log_login_attempt(user.id if user else None, email, success=False,
                           failure_reason="bad_credentials")
        return jsonify({"error": "Invalid credentials"}), 401

    if not user.is_active:
        log_login_attempt(user.id, email, success=False, failure_reason="account_disabled")
        return jsonify({"error": "Account disabled"}), 403

    # Successful login — reset lockout counters
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.utcnow()
    db.session.commit()

    access_token = create_access_token(
        identity=user.id, additional_claims={"role": user.role.value}
    )
    refresh_token = create_refresh_token(identity=user.id)

    log_login_attempt(user.id, email, success=True)
    log_activity(user.id, "login_success")

    return jsonify({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": user.to_dict(),
    }), 200


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user or not user.is_active:
        return jsonify({"error": "Unauthorized"}), 401

    new_access_token = create_access_token(
        identity=user.id, additional_claims={"role": user.role.value}
    )
    return jsonify({"access_token": new_access_token}), 200


@auth_bp.route("/logout", methods=["POST"])
@any_authenticated
def logout():
    # Stateless JWT — actual invalidation requires a token blocklist if you
    # need server-side logout. Logged here for the audit trail regardless.
    log_activity(g.current_user.id, "logout")
    return jsonify({"status": "logged out"}), 200


@auth_bp.route("/me", methods=["GET"])
@any_authenticated
def me():
    return jsonify(g.current_user.to_dict())
