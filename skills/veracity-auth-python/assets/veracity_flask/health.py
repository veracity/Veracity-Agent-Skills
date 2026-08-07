"""Anonymous health endpoints for Flask — mirrors /health, /health/ready, /health/live."""

from __future__ import annotations

from flask import Blueprint, jsonify

bp = Blueprint("veracity_health", __name__)


@bp.get("/health")
def health():
    return jsonify({"status": "healthy"})


@bp.get("/health/ready")
def ready():
    return jsonify({"status": "ready"})


@bp.get("/health/live")
def live():
    return jsonify({"status": "alive"})
