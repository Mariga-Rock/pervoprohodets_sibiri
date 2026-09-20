"""
Сборка Flask-приложения.

Этот файл:
    1. Создаёт приложение через фабрику create_app().
    2. Регистрирует расширения (db).
    3. Регистрирует маршруты через register_routes().

Запуск — через run.py в корне проекта.
"""

import logging
import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from sqlalchemy.exc import IntegrityError

load_dotenv()

from app.extensions import db  # noqa: E402
from app.models import Run, User  # noqa: E402,F401
from app.constants import (  # noqa: E402
    DEFAULT_CALORIES,
    DEFAULT_DAY,
    DEFAULT_DISTANCE,
    DEFAULT_INVENTORY,
    DEFAULT_MORALE,
    DEFAULT_SQUAD_SIZE,
    DEFAULT_VIT_C,
    DEFAULT_WARMTH,
)

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------------
# Логирование
# ----------------------------------------------------------------------------
def _configure_logging(app):
    """Настраивает логирование приложения."""
    level = logging.DEBUG if app.debug else logging.INFO
    app.logger.setLevel(level)

    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        )

    if not app.logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s [%(name)s] %(message)s"
        ))
        app.logger.addHandler(handler)


# ----------------------------------------------------------------------------
# Фабрика приложения
# ----------------------------------------------------------------------------
def create_app():
    """Фабрика приложения. Стандартный паттерн Flask."""
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.environ.get(
        "SECRET_KEY", "dev-secret-change-me"
    )

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        database_url = (
            "postgresql+psycopg2://user:caloriealot@localhost:5432/"
            "pervoprohodets"
        )
        app.logger.warning(
            "DATABASE_URL не задан, используется дефолт: %s", database_url
        )

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
        "pool_size": 5,
        "max_overflow": 10,
        "pool_recycle": 1800,
    }

    db.init_app(app)
    _configure_logging(app)
    register_routes(app)

    return app


# ----------------------------------------------------------------------------
# ХЕЛПЕРЫ ВАЛИДАЦИИ
# ----------------------------------------------------------------------------
def _extract_tg_id(data):
    """
    Извлекает и валидирует telegram_id из тела запроса.

    Возвращает (tg_id, error_response). Если error_response не None —
    запрос нужно немедленно вернуть клиенту.
    """
    tg_id = data.get("telegram_id")

    if tg_id is None:
        return None, (jsonify({
            "status": "error",
            "message": "telegram_id обязателен",
        }), 400)

    if isinstance(tg_id, bool) or not isinstance(tg_id, int):
        return None, (jsonify({
            "status": "error",
            "message": "telegram_id должен быть числом",
        }), 400)

    if tg_id <= 0:
        return None, (jsonify({
            "status": "error",
            "message": "telegram_id должен быть положительным",
        }), 400)

    return tg_id, None


def _extract_username(data):
    """Нормализует username: trim, обрезка до 64 символов, пустое → None."""
    username = data.get("username")
    if not isinstance(username, str):
        return None
    username = username.strip()[:64]
    return username or None


# ----------------------------------------------------------------------------
# ХЕЛПЕРЫ СЕРИАЛИЗАЦИИ
# ----------------------------------------------------------------------------
def serialize_run(run):
    """Превращает объект Run в словарь для JSON-ответа."""
    return {
        "day": run.day,
        "distance_covered": run.distance_covered,
        "calories": run.calories,
        "vit_c": run.vit_c,
        "morale": run.morale,
        "warmth": run.warmth,
        "discipline": run.discipline,        # ← НОВОЕ
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


def _state_response(status, user, run=None):
    """Собирает стандартный JSON-ответ для ручек состояния."""
    payload = {"status": status, "user": serialize_user(user)}
    if run is not None:
        payload["run"] = serialize_run(run)
    return jsonify(payload), 200


# ----------------------------------------------------------------------------
# МАРШРУТЫ
# ----------------------------------------------------------------------------
def register_routes(app):
    """Регистрирует все маршруты на приложении."""
        # --------------------------------------------------------
    # / — HTML-страница игры
    # --------------------------------------------------------
    @app.route("/", methods=["GET"])
    def index():
        """Отдаёт HTML-страницу игры."""
        from flask import render_template
        return render_template("game.html")

    # --------------------------------------------------------
    # /api/get_state
    # --------------------------------------------------------
    @app.route("/api/get_state", methods=["POST"])
    def get_state():
        """Возвращает состояние игрока по его telegram_id."""
        data = request.get_json(silent=True) or {}

        tg_id, err = _extract_tg_id(data)
        if err:
            return err

        user = User.query.filter_by(telegram_id=tg_id).first()
        if not user:
            return jsonify({"status": "no_user"}), 200

        if not user.run:
            return _state_response("no_run", user)

        return _state_response("ok", user, user.run)

    # --------------------------------------------------------
    # /api/start_game
    # --------------------------------------------------------
    @app.route("/api/start_game", methods=["POST"])
    def start_game():
        """Создаёт игрока (если нет) и новую экспедицию (если нет активной)."""
        data = request.get_json(silent=True) or {}

        tg_id, err = _extract_tg_id(data)
        if err:
            return err

        username = _extract_username(data)

        user = User.query.filter_by(telegram_id=tg_id).first()

        if not user:
            user = User(telegram_id=tg_id, username=username)
            db.session.add(user)
            try:
                db.session.flush()
            except IntegrityError:
                db.session.rollback()
                user = User.query.filter_by(telegram_id=tg_id).first()
                if not user:
                    app.logger.exception(
                        "Не удалось создать/перечитать пользователя tg_id=%s",
                        tg_id,
                    )
                    return jsonify({
                        "status": "error",
                        "message": "не удалось создать пользователя",
                    }), 500
            else:
                app.logger.info("Создан новый User: tg_id=%s", tg_id)
        elif username and user.username != username:
            user.username = username

        active_run = (
            Run.query
            .filter_by(user_id=user.id)
            .order_by(Run.id.desc())
            .first()
        )

        if active_run:
            db.session.commit()
            return _state_response("already_running", user, active_run)

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

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            app.logger.exception(
                "Не удалось создать Run для user_id=%s", user.id
            )
            return jsonify({
                "status": "error",
                "message": "не удалось создать экспедицию",
            }), 500

        app.logger.info(
            "Создана новая экспедиция: user_id=%s, tg_id=%s, run_id=%s",
            user.id, tg_id, new_run.id,
        )

        return _state_response("created", user, new_run)

    # --------------------------------------------------------
    # /api/make_choice
    # --------------------------------------------------------
    @app.route("/api/make_choice", methods=["POST"])
    def make_choice():
        """
        Обрабатывает выбор игрока в ивенте.

        Запрос:
            POST /api/make_choice
            {"telegram_id": 123, "event_id": "event_frozen_elk",
             "choice_id": "eat_raw"}
        """
        data = request.get_json(silent=True) or {}

        tg_id, err = _extract_tg_id(data)
        if err:
            return err

        event_id = data.get("event_id")
        choice_id = data.get("choice_id")

        if not event_id:
            return jsonify({
                "status": "error",
                "message": "event_id обязателен",
            }), 400
        if not choice_id:
            return jsonify({
                "status": "error",
                "message": "choice_id обязателен",
            }), 400

        user = User.query.filter_by(telegram_id=tg_id).first()
        if not user:
            return jsonify({
                "status": "error",
                "message": "Игрок не найден",
            }), 404
        if not user.run:
            return jsonify({
                "status": "error",
                "message": "У игрока нет активной экспедиции",
            }), 404

        from app.events_parser import process_event_choice

        result = process_event_choice(user.run, event_id, choice_id)

        if result["status"] == "error":
            return jsonify(result), 400

        run = result["run"]

        return jsonify({
            "status": "ok",
            "next_event": result["next_event"],
            "run": serialize_run(run),
        }), 200
            # --------------------------------------------------------
    # /api/next_turn
    # --------------------------------------------------------
    @app.route("/api/next_turn", methods=["POST"])
    def next_turn():
        """
        Игрок нажимает «Идти дальше». Один ход = один день.

        Логика:
            1. Налог на жизнь: списываем калории и витамин C.
            2. Проверка смерти.
            3. Генерация события дня (движок вероятностей).
            4. Если ивент — ставим current_event_id.
            5. Если тихий день — возвращаем нейтральное сообщение.
        """
        data = request.get_json(silent=True) or {}

        tg_id, err = _extract_tg_id(data)
        if err:
            return err

        user = User.query.filter_by(telegram_id=tg_id).first()
        if not user:
            return jsonify({
                "status": "error",
                "message": "Игрок не найден",
            }), 404
        if not user.run:
            return jsonify({
                "status": "error",
                "message": "У игрока нет активной экспедиции",
            }), 404

        run = user.run

        # Нельзя идти дальше, пока не разобрался с текущим ивентом
        if run.current_event_id:
            return jsonify({
                "status": "error",
                "message": (
                    f"Игрок находится в ивенте '{run.current_event_id}'. "
                    f"Сначала сделай выбор."
                ),
            }), 400

        # ---- НАЛОГ НА ЖИЗНЬ ----
        # Еда: 2 калории на человека в день.
        # 10 человек = 20 калорий. 5 человек = 10 калорий.
        run.calories -= run.squad_size * 2
        # Витамин C: жёсткая константа.
        run.vit_c -= 3
        run.day += 1

        # ---- ПРОВЕРКА СМЕРТИ ----
        game_over_reason = None
        if run.squad_size <= 0:
            game_over_reason = "Отряд погиб."
        elif run.calories <= 0:
            game_over_reason = "Отряд умер от голода."
        elif run.vit_c <= 0:
            game_over_reason = "Цинга выкосила всех."
        elif run.morale <= 0:
            game_over_reason = "Отряд взбунтовался и ушёл."

        if game_over_reason:
            user.total_deaths += 1
            db.session.delete(run)
            db.session.commit()
            app.logger.info(
                "Game Over: tg_id=%s, reason=%s, day=%s",
                tg_id, game_over_reason, run.day,
            )
            return jsonify({
                "status": "game_over",
                "reason": game_over_reason,
                "day": run.day,
                "distance_covered": run.distance_covered,
            }), 200

        # ---- ГЕНЕРАЦИЯ СОБЫТИЯ ДНЯ ----
        from app.events_engine import generate_daily_event

        event_id = generate_daily_event(run)

        if event_id:
            run.current_event_id = event_id

        # flag_modified — потому что движок мог добавить тег seen_<id>
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(run, "tags")

        db.session.commit()

        # ---- ОТВЕТ ФРОНТЕНДУ ----
        if event_id:
            from app.events_loader import get_event
            event_data = get_event(event_id)

            # Фильтруем choices по conditions — недоступные кнопки
            # фронтенд сам решит, показать серыми или скрыть.
            choices = []
            for ch in event_data["choices"]:
                choices.append({
                    "choice_id": ch["choice_id"],
                    "text": ch["text"],
                    "conditions": ch.get("conditions") or {},
                })

            return jsonify({
                "status": "ok",
                "type": "event",
                "event_id": event_id,
                "event_title": event_data.get("title", ""),
                "event_text": event_data["text"],
                "choices": choices,
                "run": serialize_run(run),
            }), 200

        # Тихий день
        return jsonify({
            "status": "ok",
            "type": "quiet_day",
            "message": "Вы прошли ещё один день. Ветер стих. "
                       "Ничего не случилось.",
            "run": serialize_run(run),
        }), 200
        # --------------------------------------------------------
    # /api/get_event
    # --------------------------------------------------------
    @app.route("/api/get_event", methods=["POST"])
    def get_event():
        """
        Возвращает данные ивента по event_id.

        Нужен для двух сценариев:
            1. Chain-ивент: игрок перешёл в следующий ивент, фронтенд
               запрашивает его текст.
            2. Восстановление сессии: игрок закрыл Telegram в середине
               ивента, открыл заново — get_state отдал current_event_id,
               фронтенд запрашивает текст.
        """
        data = request.get_json(silent=True) or {}

        tg_id, err = _extract_tg_id(data)
        if err:
            return err

        event_id = data.get("event_id")
        if not event_id:
            return jsonify({
                "status": "error",
                "message": "event_id обязателен",
            }), 400

        user = User.query.filter_by(telegram_id=tg_id).first()
        if not user:
            return jsonify({
                "status": "error",
                "message": "Игрок не найден",
            }), 404
        if not user.run:
            return jsonify({
                "status": "error",
                "message": "У игрока нет активной экспедиции",
            }), 404

        run = user.run

        # Защита: игрок может запросить только тот ивент, в котором он
        if run.current_event_id != event_id:
            return jsonify({
                "status": "error",
                "message": (
                    f"Игрок в ивенте '{run.current_event_id}', "
                    f"а запрошен '{event_id}'"
                ),
            }), 400

        from app.events_loader import get_event as load_event
        event_data = load_event(event_id)
        if not event_data:
            return jsonify({
                "status": "error",
                "message": f"Ивент '{event_id}' не найден в events.json",
            }), 404

        choices = []
        for ch in event_data["choices"]:
            choices.append({
                "choice_id": ch["choice_id"],
                "text": ch["text"],
                "conditions": ch.get("conditions") or {},
            })

        return jsonify({
            "status": "ok",
            "event_id": event_id,
            "event_title": event_data.get("title", ""),
            "event_text": event_data["text"],
            "choices": choices,
            "run": serialize_run(run),
        }), 200
