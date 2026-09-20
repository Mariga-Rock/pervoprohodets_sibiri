"""
Сборка Flask-приложения.

Этот файл:
    1. Создаёт приложение через фабрику create_app().
    2. Регистрирует расширения (db).
    3. Регистрирует маршруты через register_routes().

Запуск — через run.py в корне проекта.
"""

import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify

load_dotenv()

from app.extensions import db
from app.models import User, Run  # noqa: F401
from app.constants import (
    DEFAULT_CALORIES, DEFAULT_VIT_C, DEFAULT_MORALE, DEFAULT_WARMTH,
    DEFAULT_SQUAD_SIZE, DEFAULT_DAY, DEFAULT_DISTANCE, DEFAULT_INVENTORY,
)


def create_app():
    """Фабрика приложения. Стандартный паттерн Flask."""
    app = Flask(__name__)

    app.config['SECRET_KEY'] = os.environ.get(
        'SECRET_KEY', 'dev-secret-change-me'
    )
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL', 'sqlite:///app.db'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    register_routes(app)

    return app


# ============================================================
# ХЕЛПЕРЫ СЕРИАЛИЗАЦИИ
# ============================================================
def serialize_run(run):
    """Превращает объект Run в словарь для JSON-ответа."""
    return {
        "day": run.day,
        "distance_covered": run.distance_covered,
        "calories": run.calories,
        "vit_c": run.vit_c,
        "morale": run.morale,
        "warmth": run.warmth,
        "squad_size": run.squad_size,
        "inventory": run.inventory,
        "tags": run.tags,
        "current_event_id": run.current_event_id,
    }


def serialize_user(user):
    """Превращает объект User в словарь для JSON-ответа."""
    return {
        "telegram_id": user.telegram_id,
        "username": user.username,
        "total_deaths": user.total_deaths,
        "purchased_dlc": user.purchased_dlc,
    }


# ============================================================
# МАРШРУТЫ
# ============================================================
def register_routes(app):
    """Регистрирует все маршруты на приложении."""

    @app.route('/api/get_state', methods=['POST'])
    def get_state():
        """Возвращает состояние игрока по его telegram_id."""
        data = request.get_json(silent=True) or {}
        tg_id = data.get('telegram_id')

        if not tg_id:
            return jsonify({
                "status": "error",
                "message": "telegram_id обязателен"
            }), 400

        if not isinstance(tg_id, int):
            return jsonify({
                "status": "error",
                "message": "telegram_id должен быть числом"
            }), 400

        user = User.query.filter_by(telegram_id=tg_id).first()

        if not user:
            return jsonify({"status": "no_user"}), 200

        if not user.run:
            return jsonify({
                "status": "no_run",
                "user": serialize_user(user)
            }), 200

        return jsonify({
            "status": "ok",
            "user": serialize_user(user),
            "run": serialize_run(user.run)
        }), 200

    @app.route('/api/start_game', methods=['POST'])
    def start_game():
        """Создаёт игрока (если нет) и новую экспедицию (если нет активной)."""
        data = request.get_json(silent=True) or {}
        tg_id = data.get('telegram_id')
        username = data.get('username')

        if not tg_id:
            return jsonify({
                "status": "error",
                "message": "telegram_id обязателен"
            }), 400

        if not isinstance(tg_id, int):
            return jsonify({
                "status": "error",
                "message": "telegram_id должен быть числом"
            }), 400

        user = User.query.filter_by(telegram_id=tg_id).first()

        if not user:
            user = User(telegram_id=tg_id, username=username)
            db.session.add(user)
            db.session.flush()
            app.logger.info(f"Создан новый User: tg_id={tg_id}")
        else:
            if username and user.username != username:
                user.username = username

        if user.run:
            db.session.commit()
            return jsonify({
                "status": "already_running",
                "user": serialize_user(user),
                "run": serialize_run(user.run),
            }), 200

        new_run = Run(
            user_id=user.id,
            day=DEFAULT_DAY,
            distance_covered=DEFAULT_DISTANCE,
            calories=DEFAULT_CALORIES,
            vit_c=DEFAULT_VIT_C,
            morale=DEFAULT_MORALE,
            warmth=DEFAULT_WARMTH,
            squad_size=DEFAULT_SQUAD_SIZE,
            inventory=dict(DEFAULT_INVENTORY),
            tags=[],
        )
        db.session.add(new_run)
        db.session.commit()

        app.logger.info(
            f"Создана новая экспедиция: user_id={user.id}, "
            f"tg_id={tg_id}, run_id={new_run.id}"
        )

        return jsonify({
            "status": "created",
            "user": serialize_user(user),
            "run": serialize_run(new_run),
        }), 200
