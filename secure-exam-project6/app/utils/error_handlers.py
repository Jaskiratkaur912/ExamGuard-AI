"""
Centralized error handlers — consistent JSON error shape for the frontend,
and a single place that prevents stack traces / internals from leaking to
clients (a basic but important security hygiene point).
"""
from flask import jsonify
from app.utils.validation import ValidationError


def register_error_handlers(app):

    @app.errorhandler(ValidationError)
    def handle_validation_error(err):
        return jsonify({"error": err.message, "field": err.field}), 400

    @app.errorhandler(404)
    def handle_not_found(err):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(403)
    def handle_forbidden(err):
        return jsonify({"error": "Forbidden"}), 403

    @app.errorhandler(401)
    def handle_unauthorized(err):
        return jsonify({"error": "Unauthorized"}), 401

    @app.errorhandler(500)
    def handle_internal_error(err):
        app.logger.exception("Unhandled server error")
        return jsonify({"error": "Internal server error"}), 500
