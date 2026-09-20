"""
Сборка Flask-приложения.

Файл содержит:
    1. Фабрику create_app().
    2. Регистрацию расширений (db).
    3. Маршруты через register_routes(app).
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


def _configure_logging(app):
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


def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.environ.get(
        "SECRET_KEY", "dev-secret-change-me"
    )

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        database_url = (
            "postgresql+psycopg2://user:caloriealot@localhost:5432/"
            "pervoprokhodets"
        )
        app.logger.warning("DATABASE_URL не задан, дефолт: %s", database_url)

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


# ============================================================
# ХЕЛПЕРЫ
# ============================================================
def _extract_tg_id(data):
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
    username = data.get("username")
    if not isinstance(username, str):
        return None
    username = username.strip()[:64]
    return username or None


def _calculate_speed(run):
    """
    Сколько вёрст отряд пройдёт за день.
    Раненые не идут — каждый отнимает версту от скорости.
    """
    speed = 3.0
    if run.vit_c < 30:
        speed = min(speed, 2.0)
    if run.morale < 20:
        speed = min(speed, 1.0)
    if run.squad_size <= 5:
        speed *= 0.7
    if run.squad_size <= 2:
        speed *= 0.4
    if (run.wounded or 0) > 0:
        speed = max(1.0, speed - run.wounded)
    if (run.inventory or {}).get("dog_sled"):
        speed = max(speed, 5.0)
    return max(1, int(speed))


def serialize_run(run):
    return {
        "day": run.day,
        "distance_covered": run.distance_covered,
        "calories": run.calories,
        "vit_c": run.vit_c,
        "morale": run.morale,
        "warmth": run.warmth,
        "discipline": run.discipline,
        "has_priest": run.has_priest,
        "wounded": run.wounded,
        "squad_size": run.squad_size,
        "inventory": run.inventory,
        "tags": run.tags,
        "recent_events": run.recent_events,
        "current_event_id": run.current_event_id,
    }


def serialize_user(user):
    return {
        "telegram_id": user.telegram_id,
        "username": user.username,
        "total_deaths": user.total_deaths,
        "purchased_dlc": user.purchased_dlc,
    }


def _state_response(status, user, run=None):
    payload = {"status": status, "user": serialize_user(user)}
    if run is not None:
        payload["run"] = serialize_run(run)
    return jsonify(payload), 200


# ============================================================
# МАРШРУТЫ
# ============================================================
def register_routes(app):

    # --------------------------------------------------------
    # / — HTML
    # --------------------------------------------------------
    @app.route("/", methods=["GET"])
    def index():
        from flask import render_template
        return render_template("game.html")

    # --------------------------------------------------------
    # /api/get_state
    # --------------------------------------------------------
    @app.route("/api/get_state", methods=["POST"])
    def get_state():
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
                    app.logger.exception("Не удалось создать user tg_id=%s", tg_id)
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
            recent_events=[],
        )
        db.session.add(new_run)

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            app.logger.exception("Не удалось создать Run user_id=%s", user.id)
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
    # /api/get_event
    # --------------------------------------------------------
    @app.route("/api/get_event", methods=["POST"])
    def get_event():
        data = request.get_json(silent=True) or {}
        tg_id, err = _extract_tg_id(data)
        if err:
            return err

        event_id = data.get("event_id")
        if not event_id:
            return jsonify({
                "status": "error", "message": "event_id обязателен",
            }), 400

        user = User.query.filter_by(telegram_id=tg_id).first()
        if not user or not user.run:
            return jsonify({
                "status": "error", "message": "Нет активной экспедиции",
            }), 404

        run = user.run
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
                "message": f"Ивент '{event_id}' не найден",
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

    # --------------------------------------------------------
    # /api/make_choice
    # --------------------------------------------------------
    @app.route("/api/make_choice", methods=["POST"])
    def make_choice():
        data = request.get_json(silent=True) or {}
        tg_id, err = _extract_tg_id(data)
        if err:
            return err

        event_id = data.get("event_id")
        choice_id = data.get("choice_id")

        if not event_id:
            return jsonify({
                "status": "error", "message": "event_id обязателен",
            }), 400
        if not choice_id:
            return jsonify({
                "status": "error", "message": "choice_id обязателен",
            }), 400

        user = User.query.filter_by(telegram_id=tg_id).first()
        if not user or not user.run:
            return jsonify({
                "status": "error", "message": "Нет активной экспедиции",
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
            "consequences": result.get("consequences"),
        }), 200

    # --------------------------------------------------------
    # /api/next_turn
    # --------------------------------------------------------
    @app.route("/api/next_turn", methods=["POST"])
    def next_turn():
        data = request.get_json(silent=True) or {}
        tg_id, err = _extract_tg_id(data)
        if err:
            return err

        user = User.query.filter_by(telegram_id=tg_id).first()
        if not user or not user.run:
            return jsonify({
                "status": "error", "message": "Нет активной экспедиции",
            }), 404

        run = user.run

        if run.current_event_id:
            return jsonify({
                "status": "error",
                "message": (
                    f"Игрок находится в ивенте '{run.current_event_id}'. "
                    f"Сначала сделай выбор."
                ),
            }), 400

        from sqlalchemy.orm.attributes import flag_modified

        # НАЛОГ НА ЖИЗНЬ
        run.calories -= run.squad_size * 2
        run.vit_c -= 3
        run.day += 1

        # ДВИЖЕНИЕ ПО МАРШРУТУ
        speed = _calculate_speed(run)
        run.distance_covered += speed

        # ВОССТАНОВЛЕНИЕ РАНЕНЫХ
        # 1 боец в день, если есть травы.
        if run.wounded > 0 and run.inventory.get("herbs", 0) > 0:
            run.inventory["herbs"] -= 1
            if run.inventory["herbs"] <= 0:
                del run.inventory["herbs"]
            run.wounded -= 1
            flag_modified(run, "inventory")

        # СМЕРТЬ
        game_over_reason = None
                # ГОЛОД — страдание, но не смерть до 30-го дня
        if run.calories <= 0:
            run.calories = 0  # не уходит в минус для отображения
            run.morale = max(0, run.morale - 5)
            if run.day % 3 == 0:
                run.wounded = run.wounded + 1  # ослабевшие от истощения
            if run.day % 7 == 0 and run.squad_size > 1:
                run.squad_size -= 1  # кто-то умер от истощения

        # СМЕРТЬ
        game_over_reason = None
        if run.squad_size <= 0:
            game_over_reason = "Отряд погиб."
        elif run.vit_c <= 0:
            game_over_reason = "Цинга выкосила всех."
        elif run.morale <= 0:
            game_over_reason = "Отряд взбунтовался и ушёл."
        elif run.calories <= 0 and run.day >= 30:
            game_over_reason = "Отряд умер от голода."

        if game_over_reason:
            day_died = run.day
            dist = run.distance_covered
            user.total_deaths += 1
            db.session.delete(run)
            db.session.commit()
            app.logger.info(
                "Game Over: tg_id=%s, reason=%s, day=%s",
                tg_id, game_over_reason, day_died,
            )
            return jsonify({
                "status": "game_over",
                "reason": game_over_reason,
                "day": day_died,
                "distance_covered": dist,
            }), 200

        # ПОБЕДА
        if run.distance_covered >= 100:
            day_won = run.day
            dist = run.distance_covered
            user.total_deaths += 0
            db.session.delete(run)
            db.session.commit()
            return jsonify({
                "status": "victory",
                "day": day_won,
                "distance_covered": dist,
            }), 200

        # ПРИОРИТЕТНЫЕ СОБЫТИЯ
        PRIORITY_EVENTS = {"need_funeral": "event_funeral"}

        priority_event_id = None
        for tag, event_id in PRIORITY_EVENTS.items():
            if tag in run.tags:
                if event_id == "event_funeral" and not run.has_priest:
                    run.tags.remove(tag)
                    flag_modified(run, "tags")
                    app.logger.info("Нет священника — молебен пропущен")
                    continue

                priority_event_id = event_id
                run.tags.remove(tag)
                flag_modified(run, "tags")
                break

        if priority_event_id:
            run.current_event_id = priority_event_id
            db.session.commit()

            from app.events_loader import get_event as load_event
            event_data = load_event(priority_event_id)
            choices = [
                {
                    "choice_id": ch["choice_id"],
                    "text": ch["text"],
                    "conditions": ch.get("conditions") or {},
                }
                for ch in event_data["choices"]
            ]
            return jsonify({
                "status": "ok",
                "type": "event",
                "event_id": priority_event_id,
                "event_title": event_data.get("title", ""),
                "event_text": event_data["text"],
                "choices": choices,
                "run": serialize_run(run),
            }), 200

        # ОБЫЧНАЯ ГЕНЕРАЦИЯ
        from app.events_engine import generate_daily_event
        event_id = generate_daily_event(run)

        if event_id:
            run.current_event_id = event_id

        flag_modified(run, "tags")

        db.session.commit()

        if event_id:
            from app.events_loader import get_event as load_event
            event_data = load_event(event_id)
            choices = [
                {
                    "choice_id": ch["choice_id"],
                    "text": ch["text"],
                    "conditions": ch.get("conditions") or {},
                }
                for ch in event_data["choices"]
            ]
            return jsonify({
                "status": "ok",
                "type": "event",
                "event_id": event_id,
                "event_title": event_data.get("title", ""),
                "event_text": event_data["text"],
                "choices": choices,
                "run": serialize_run(run),
            }), 200

        # ТИХИЙ ДЕНЬ
        food_spent = run.squad_size * 2
        return jsonify({
            "status": "ok",
            "type": "quiet_day",
            "message": (
                f"День прошёл спокойно. Отряд шёл по тайге, "
                f"не встретив ни зверя, ни человека."
            ),
            "deltas": [
                f"−{food_spent} калорий",
                "−3 витамина C",
            ],
            "run": serialize_run(run),
        }), 200

    # --------------------------------------------------------
    # /api/do_action
    # --------------------------------------------------------
    @app.route("/api/do_action", methods=["POST"])
    def do_action():
        data = request.get_json(silent=True) or {}
        tg_id, err = _extract_tg_id(data)
        if err:
            return err

        action_type = data.get("action_type")
        if action_type not in ("wood", "hunt", "fish", "herbs", "pine", "rest"):
            return jsonify({
                "status": "error", "message": "Неизвестное действие",
            }), 400

        user = User.query.filter_by(telegram_id=tg_id).first()
        if not user or not user.run:
            return jsonify({
                "status": "error", "message": "Нет активной экспедиции",
            }), 404

        run = user.run
        if run.current_event_id:
            return jsonify({
                "status": "error",
                "message": f"Вы в ивенте '{run.current_event_id}'",
            }), 400

        import random
        from sqlalchemy.orm.attributes import flag_modified

        # Налог на день
        run.calories -= run.squad_size * 2
        run.vit_c -= 3
        run.day += 1
        run.warmth = max(0, run.warmth - 5)

        if run.calories <= 0:
            run.calories = 0
            run.morale = max(0, run.morale - 5)
            if run.day % 3 == 0:
                run.wounded = run.wounded + 1
            if run.day % 7 == 0 and run.squad_size > 1:
                run.squad_size -= 1

        if run.squad_size <= 0 or run.vit_c <= 0 or run.morale <= 0 or (
            run.calories <= 0 and run.day >= 30
        ):
            reason = None
            if run.squad_size <= 0:
                reason = "Отряд погиб."
            elif run.vit_c <= 0:
                reason = "Цинга выкосила всех."
            elif run.morale <= 0:
                reason = "Отряд взбунтовался и ушёл."
            elif run.calories <= 0 and run.day >= 30:
                reason = "Отряд умер от голода."

            day_died = run.day
            dist = run.distance_covered
            user.total_deaths += 1
            db.session.delete(run)
            db.session.commit()
            return jsonify({
                "status": "game_over",
                "reason": reason,
                "day": day_died,
                "distance_covered": dist,
            }), 200

        text = ""
        deltas = []

        if action_type == "wood":
            amount = random.randint(3, 7)
            run.inventory["wood"] = run.inventory.get("wood", 0) + amount
            text = ("Отряд рубил сухостой весь день. Топоры тупились, "
                    "но к вечеру у костра лежала хорошая поленница.")
            deltas = [f"+{amount} дров"]

        elif action_type == "hunt":
            if run.squad_size < 3:
                text = "Отряд слишком мал для охоты."
                deltas = ["Ничего не добыли"]
            else:
                roll = random.random()
                if roll < 0.4:
                    meat = random.randint(2, 4)
                    run.inventory["salted_meat"] = (
                        run.inventory.get("salted_meat", 0) + meat
                    )
                    text = ("Нашли оленя в распадке. Бились с ним полдня, "
                            "но завалили.")
                    deltas = [f"+{meat} солёного мяса"]
                elif roll < 0.7:
                    run.inventory["fur"] = run.inventory.get("fur", 0) + 1
                    text = ("Повезло на белку. Полдюжины шкурок — "
                            "не мясо, но пушнина в цене.")
                    deltas = ["+1 пушнина"]
                else:
                    text = "Зверь ушёл. Три часа гнались по ложному следу."
                    deltas = ["Ничего не добыли"]

        elif action_type == "fish":
            amount = random.randint(2, 5)
            run.inventory["fish"] = run.inventory.get("fish", 0) + amount
            run.vit_c = min(100, run.vit_c + 5)
            text = ("Прорубили лунку, тягали сети. Рыба шла вяло, "
                    "но что-то поймали.")
            deltas = [f"+{amount} рыбы", "+5 к витамину C"]

        elif action_type == "herbs":
            amount = random.randint(1, 4)
            run.inventory["herbs"] = run.inventory.get("herbs", 0) + amount
            text = ("Собирали травы по склонам весь день. "
                    "Кое-что нашли.")
            deltas = [f"+{amount} трав"]

        elif action_type == "pine":
            run.vit_c = min(100, run.vit_c + 15)
            run.morale = min(100, run.morale + 5)
            text = ("Собирали хвою кедрового стланика, варили горький отвар. "
                    "Пили по кружке — жжёт, но по жилам разливается тепло. "
                    "Цинга отступает.")
            deltas = ["+15 к витамину C", "+5 к морали"]

        elif action_type == "rest":
            run.morale = min(100, run.morale + 15)
            run.warmth = min(100, run.warmth + 10)
            text = ("День стояли лагерем. Спали, чинили одежду, "
                    "точили сабли. У костра пели песни. Отряд отдохнул.")
            deltas = ["+15 к морали", "+10 к теплу"]
            if run.wounded > 0:
                run.wounded -= 1
                deltas.append("−1 раненых")

        deltas.append(f"−{run.squad_size * 2} калорий")
        deltas.append("−3 витамина C")
        deltas.append("−5 тепла")

        flag_modified(run, "inventory")
        db.session.commit()

        return jsonify({
            "status": "ok",
            "type": "action",
            "action_type": action_type,
            "narrative": text,
            "deltas": deltas,
            "run": serialize_run(run),
        }), 200
