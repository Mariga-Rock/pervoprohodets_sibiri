"""Сборка Flask-приложения."""
import logging
import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from sqlalchemy.exc import IntegrityError

load_dotenv()

from app.extensions import db  # noqa: E402
from app.models import Run, Traveler, User  # noqa: E402,F401
from app.constants import (  # noqa: E402
    DAILY_FOOD_PER_PERSON,
    DEFAULT_CRANBERRIES, DEFAULT_DAY, DEFAULT_DISTANCE,
    DEFAULT_FISH, DEFAULT_FLOUR, DEFAULT_INVENTORY, DEFAULT_MEAT,
    DEFAULT_MORALE, DEFAULT_VIT_C, DEFAULT_WARMTH,
    DRUNKARD_MONEY_THRESHOLD,
    FISH_PER_DAY, FUR_PER_CHARTER, FUR_PRICE,
    HUNGER_DEATH_DAY, MEAT_PER_DAY,
    SCURVY_RECOVERY_DAYS, SCURVY_START_DAYS,
    VIT_FROM_BERRIES, VIT_FROM_FISH, VIT_FROM_MEAT, VIT_FROM_PINE,
    STARTING_TRAVELERS,
    TITLE_MAGNATE_THRESHOLD, TITLE_NOBLE_THRESHOLD,
    city_charter_cost, hunting_synergy,
)
from app.advisor import get_advisor_hint  # noqa: E402
from app.achievements import check_achievements  # noqa: E402
from app import season as season_mod  # noqa: E402

logger = logging.getLogger(__name__)


def _configure_logging(app):
    level = logging.DEBUG if app.debug else logging.INFO
    app.logger.setLevel(level)
    if not logging.getLogger().handlers:
        logging.basicConfig(level=level,
                            format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
    if not app.logger.handlers:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s [%(name)s] %(message)s"))
        app.logger.addHandler(h)


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    url = os.environ.get("DATABASE_URL") or \
          "postgresql+psycopg2://user:caloriealot@localhost:5432/pervoprokhodets"
    app.config["SQLALCHEMY_DATABASE_URI"] = url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True, "pool_size": 5,
        "max_overflow": 10, "pool_recycle": 1800,
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
        return None, (jsonify({"status": "error", "message": "telegram_id обязателен"}), 400)
    if isinstance(tg_id, bool) or not isinstance(tg_id, int):
        return None, (jsonify({"status": "error", "message": "telegram_id должен быть числом"}), 400)
    if tg_id <= 0:
        return None, (jsonify({"status": "error", "message": "telegram_id должен быть положительным"}), 400)
    return tg_id, None


def _extract_username(data):
    username = data.get("username")
    if not isinstance(username, str):
        return None
    return username.strip()[:64] or None


def _has_priest(run):
    return any(t.is_priest and t.alive for t in run.travelers)


def _calculate_speed(run):
    speed = 3.0
    if run.vit_c < 30:
        speed = min(speed, 2.0)
    if run.morale < 20:
        speed = min(speed, 1.0)
    if run.squad_size <= 5:
        speed *= 0.7
    if run.squad_size <= 2:
        speed *= 0.4
    non_walking = (run.wounded or 0) + (run.caretaker_count or 0)
    if non_walking > 0:
        speed = max(1.0, speed - non_walking)
    if (run.inventory or {}).get("dog_sled"):
        speed = max(speed, 5.0)
    # Зимой медленнее
    if run.season == 3:
        speed *= 0.8
    return max(1, int(speed))


def _consume_food(run):
    need = run.squad_size * DAILY_FOOD_PER_PERSON
    # Зимой едят больше
    if run.season == 3:
        need = int(need * 1.3)
    if need <= 0:
        return True
    if run.flour >= need:
        run.flour -= need
        run.hunger_days = 0
        return True
    if run.flour + run.fish >= need:
        r = need - run.flour
        run.flour = 0
        run.fish -= r
        run.hunger_days = 0
        return True
    if run.flour + run.fish + run.meat >= need:
        r = need - run.flour - run.fish
        run.flour = 0
        run.fish = 0
        run.meat -= r
        run.hunger_days = 0
        return True
    run.flour = 0
    run.fish = 0
    run.meat = 0
    run.hunger_days += 1
    run.morale = max(0, run.morale - 5)
    if run.hunger_days % 3 == 0:
        from app.events_parser import _wound_random_traveler
        _wound_random_traveler(run)
    return False


def _tick_vitamin_and_scurvy(run, vitamin_used_today=False):
    """
    Обновляет витамин C и цингу.
    vitamin_used_today — True, если игрок сегодня использовал источник
    (в этом случае days_without_vit уже сброшен вызывающим кодом).
    """
    from sqlalchemy.orm.attributes import flag_modified

    # 1. Деградация витамина
    if not vitamin_used_today:
        season_mod.degrade_vit_c(run)
    # Если использовал — days_without_vit уже 0

    # 2. Цинга начинается
    if (run.days_without_vit >= SCURVY_START_DAYS
            and not run.scurvy_active):
        run.scurvy_active = True
        from app.events_parser import _progress_scurvy
        _progress_scurvy(run)
        _progress_scurvy(run)  # 2 больных сразу

    # 3. Если цинга активна — прогрессия
    if run.scurvy_active:
        from app.events_parser import _progress_scurvy
        if run.day % 2 == 0:  # каждый второй день +1 больной
            _progress_scurvy(run)
        # Больные теряют endurance
        for t in run.travelers:
            if t.alive and t.scurvy:
                t.endurance -= 1
                if t.endurance <= 0:
                    t.alive = False
        # Восстановление: 3 дня с витамином подряд
        if run.days_without_vit == 0:
            run.scurvy_recovery_days = (run.scurvy_recovery_days or 0) + 1
            if run.scurvy_recovery_days >= SCURVY_RECOVERY_DAYS:
                run.scurvy_active = False
                run.scurvy_recovery_days = 0
                for t in run.travelers:
                    if t.alive and t.scurvy:
                        t.scurvy = False
                        t.scurvy_refused = False
                        t.scurvy_healer_seen = False
        else:
            run.scurvy_recovery_days = 0


def _check_story_event(run):
    """Сюжетные триггеры."""
    import random
    from sqlalchemy.orm.attributes import flag_modified

    # Осада
    if run.siege_days_left > 0:
        if "siege_hunger_done" not in run.tags and run.siege_days_left <= 12:
            run.tags.append("siege_hunger_done")
            flag_modified(run, "tags")
            return "event_siege_hunger"
        if "siege_assault_done" not in run.tags and run.siege_days_left <= 9:
            run.tags.append("siege_assault_done")
            flag_modified(run, "tags")
            return "event_siege_assault"
        if "siege_koltso_done" not in run.tags and run.siege_days_left <= 6:
            run.tags.append("siege_koltso_done")
            flag_modified(run, "tags")
            return "event_siege_koltso"
        if "siege_end_done" not in run.tags and run.siege_days_left <= 1:
            run.tags.append("siege_end_done")
            flag_modified(run, "tags")
            return "event_siege_end"
        return None

    # Цинга (приоритетно)
    if run.scurvy_active and "scurvy_event_done" not in run.tags:
        run.tags.append("scurvy_event_done")
        flag_modified(run, "tags")
        return "event_scurvy_start"

    if run.distance_covered >= 10 and "rumor_1_done" not in run.tags:
        run.tags.append("rumor_1_done")
        flag_modified(run, "tags")
        return "event_first_rumor"

    if run.distance_covered >= 25 and run.isker_status == "none":
        return "event_chuvash_mys"

    if run.isker_status == "taken" and "isker_fortified" not in run.tags:
        run.tags.append("isker_fortified")
        flag_modified(run, "tags")
        return "event_fortify_isker"

    if (run.distance_covered >= 35 and run.mangazeya_rumors >= 1
            and "rumor_2_done" not in run.tags):
        run.tags.append("rumor_2_done")
        flag_modified(run, "tags")
        return "event_second_rumor"

    if (run.isker_status == "taken" and run.distance_covered >= 45
            and "siege_started" not in run.tags):
        run.siege_days_left = random.randint(10, 15)
        run.isker_status = "under_siege"
        run.tags.append("siege_started")
        flag_modified(run, "tags")
        return "event_siege_start"

    if run.yasak_count >= 5 and "yasak_triggered" not in run.tags:
        run.tags.append("yasak_triggered")
        flag_modified(run, "tags")
        return "event_yasak_sent"

    if ("selkup_risky" in run.tags
            and "selkup_revolt_done" not in run.tags):
        if random.random() < 0.15:
            run.tags.append("selkup_revolt_done")
            flag_modified(run, "tags")
            return "event_selkup_revolt"

    if run.distance_covered >= 75 and not run.volhovsky_arrived:
        return "event_volhovsky_arrives"

    if (run.volhovsky_arrived and not run.volhovsky_healed
            and "volhovsky_sick_done" not in run.tags):
        run.tags.append("volhovsky_sick_done")
        flag_modified(run, "tags")
        return "event_volhovsky_sick"

    if (run.volhovsky_healed
            and "volhovsky_recovers_done" not in run.tags):
        run.tags.append("volhovsky_recovers_done")
        flag_modified(run, "tags")
        return "event_volhovsky_recovers"

    if run.distance_covered >= 90 and "vagai_done" not in run.tags:
        run.tags.append("vagai_done")
        flag_modified(run, "tags")
        return "event_vagai_night"

    if run.distance_covered >= 95 and "samoyed_done" not in run.tags:
        run.tags.append("samoyed_done")
        flag_modified(run, "tags")
        return "event_samoyed_camp"

    if run.distance_covered >= 100 and "mangazeya_done" not in run.tags:
        run.tags.append("mangazeya_done")
        flag_modified(run, "tags")
        return "event_mangazeya_land"

    return None


def _build_story_event_response(run, event_id, ach, hint):
    from app.events_loader import get_event as load_event
    ed = load_event(event_id)
    choices = [{"choice_id": ch["choice_id"], "text": ch["text"],
                "conditions": ch.get("conditions") or {}}
               for ch in ed["choices"]]
    return jsonify({
        "status": "ok", "type": "event",
        "event_id": event_id,
        "event_title": ed.get("title", ""),
        "event_text": ed["text"],
        "choices": choices,
        "advisor_hint": hint,
        "achievements": ach,
        "run": serialize_run(run),
    }), 200


def _build_epilogue(run, user):
    lines = []
    lines.append(f"Вы прошли {run.distance_covered} вёрст за {run.day} дней.")
    if "isker_garrison" in run.tags:
        lines.append("Искер взят и укреплён гарнизоном. Первый русский острог на Иртыше.")
    elif "isker_burned" in run.tags:
        lines.append("Искер сожжён. Кучуму негде сесть.")
    elif "isker_lost" in run.tags:
        lines.append("Искер оставлен. Татары вернулись в него.")
    elif run.isker_status == "relieved":
        lines.append("Искер выстоял осаду. Казаки удержали город.")
    elif run.isker_status == "taken":
        lines.append("Искер взят, но не удержан.")
    else:
        lines.append("Искер не был взят.")

    if run.yasak_count >= 5:
        lines.append("Пять племён признали руку московского царя. Ясак отправлен в Москву.")
    elif run.yasak_count >= 1:
        lines.append(f"Ясак собран с {run.yasak_count} племён.")
    else:
        lines.append("Ясак собрать не удалось.")

    if run.ivan_koltso_alive:
        lines.append("Иван Кольцо выжил и стоял рядом до конца похода.")
    else:
        lines.append("Иван Кольцо погиб на переговорах с Карачой.")

    if run.ermak_alive:
        lines.append("Ермак Тимофеевич выжил на Вагае и дошёл до реки Таз.")
    else:
        lines.append("Ермак Тимофеевич погиб на Вагае. Отряд вёл Матвей Мещеряк.")

    if run.noble_title:
        lines.append(f"Царь пожаловал титул: {run.noble_title}.")

    final = ("В 1601 году, через шестнадцать лет после вашего похода, "
             "на реке Таз воеводы Мирон Шаховской и Данила Хрипунов "
             "основали город Мангазея. Ваше открытие стало первым шагом. "
             "Сибирь помнит вас.")
    return {"headline": "Земля мангазейская", "lines": lines, "final": final}


def serialize_run(run):
    return {
        "day": run.day,
        "distance_covered": run.distance_covered,
        "season": run.season,
        "season_day": run.season_day,
        "season_name": season_mod.season_name(run),
        "flour": run.flour, "fish": run.fish, "meat": run.meat,
        "cranberries": run.cranberries,
        "hunger_days": run.hunger_days,
        "vit_c": run.vit_c,
        "days_without_vit": run.days_without_vit,
        "scurvy_active": run.scurvy_active,
        "morale": run.morale, "warmth": run.warmth,
        "discipline": run.discipline,
        "money": run.money, "charters": run.charters,
        "total_fur_sent": run.total_fur_sent,
        "cities_count": run.cities_count,
        "noble_title": run.noble_title,
        "has_priest": run.has_priest,
        "wounded": run.wounded,
        "caretaker_count": run.caretaker_count,
        "squad_size": run.squad_size,
        "alive_count": run.alive_count,
        "inventory": run.inventory, "tags": run.tags,
        "recent_events": run.recent_events,
        "current_event_id": run.current_event_id,
        "isker_status": run.isker_status,
        "siege_days_left": run.siege_days_left,
        "siege_result": run.siege_result,
        "ivan_koltso_alive": run.ivan_koltso_alive,
        "ermak_alive": run.ermak_alive,
        "leader": run.leader,
        "mangazeya_rumors": run.mangazeya_rumors,
        "yasak_count": run.yasak_count,
        "volhovsky_arrived": run.volhovsky_arrived,
        "volhovsky_alive": run.volhovsky_alive,
        "volhovsky_healed": run.volhovsky_healed,
        "travelers": [
            {"id": t.id, "name": t.name, "hunting": t.hunting,
             "endurance": t.endurance, "endurance_max": t.endurance_max,
             "is_ataman": t.is_ataman, "is_doctor": t.is_doctor,
             "is_priest": t.is_priest,
             "wounded": t.wounded,
             "wounded_days_left": t.wounded_days_left,
             "is_caretaker": t.is_caretaker,
             "caring_for": t.caring_for,
             "scurvy": t.scurvy, "alive": t.alive}
            for t in run.travelers
        ],
    }


def serialize_user(user):
    return {
        "telegram_id": user.telegram_id, "username": user.username,
        "total_deaths": user.total_deaths,
        "purchased_dlc": user.purchased_dlc,
        "achievements": user.achievements or [],
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

    @app.route("/", methods=["GET"])
    def index():
        from flask import render_template
        return render_template("game.html")

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
                    return jsonify({"status": "error",
                                    "message": "не удалось создать пользователя"}), 500
        elif username and user.username != username:
            user.username = username

        active_run = (Run.query.filter_by(user_id=user.id)
                      .order_by(Run.id.desc()).first())
        if active_run and "game_won" in (active_run.tags or []):
            db.session.delete(active_run)
            db.session.commit()
            active_run = None
        if active_run:
            db.session.commit()
            return _state_response("already_running", user, active_run)

        new_run = Run(
            user_id=user.id, day=DEFAULT_DAY,
            distance_covered=DEFAULT_DISTANCE,
            season=1, season_day=1,
            flour=DEFAULT_FLOUR, fish=DEFAULT_FISH,
            meat=DEFAULT_MEAT, cranberries=DEFAULT_CRANBERRIES,
            vit_c=DEFAULT_VIT_C, morale=DEFAULT_MORALE,
            warmth=DEFAULT_WARMTH, inventory=dict(DEFAULT_INVENTORY),
            tags=[], recent_events=[],
        )
        db.session.add(new_run)
        db.session.flush()

        for tpl in STARTING_TRAVELERS:
            t = Traveler(
                run_id=new_run.id, name=tpl["name"],
                hunting=tpl["hunting"], endurance_max=tpl["endurance_max"],
                endurance=tpl["endurance_max"],
                is_doctor=tpl["is_doctor"], is_scientist=tpl["is_scientist"],
                is_ataman=tpl["is_ataman"],
                is_priest=tpl.get("is_priest", False),
                alive=True, wounded=False,
            )
            db.session.add(t)

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return jsonify({"status": "error",
                            "message": "не удалось создать экспедицию"}), 500
        return _state_response("created", user, new_run)

    @app.route("/api/get_event", methods=["POST"])
    def get_event():
        data = request.get_json(silent=True) or {}
        tg_id, err = _extract_tg_id(data)
        if err:
            return err
        event_id = data.get("event_id")
        if not event_id:
            return jsonify({"status": "error", "message": "event_id обязателен"}), 400
        user = User.query.filter_by(telegram_id=tg_id).first()
        if not user or not user.run:
            return jsonify({"status": "error", "message": "Нет активной экспедиции"}), 404
        run = user.run
        if run.current_event_id != event_id:
            return jsonify({"status": "error",
                            "message": f"Игрок в '{run.current_event_id}'"}), 400
        from app.events_loader import get_event as load_event
        ed = load_event(event_id)
        if not ed:
            return jsonify({"status": "error", "message": f"Ивент '{event_id}' не найден"}), 404
        choices = [{"choice_id": ch["choice_id"], "text": ch["text"],
                    "conditions": ch.get("conditions") or {}}
                   for ch in ed["choices"]]
        return jsonify({
            "status": "ok", "event_id": event_id,
            "event_title": ed.get("title", ""),
            "event_text": ed["text"],
            "choices": choices, "run": serialize_run(run),
        }), 200

    @app.route("/api/make_choice", methods=["POST"])
    def make_choice():
        data = request.get_json(silent=True) or {}
        tg_id, err = _extract_tg_id(data)
        if err:
            return err
        event_id = data.get("event_id")
        choice_id = data.get("choice_id")
        if not event_id or not choice_id:
            return jsonify({"status": "error", "message": "event_id и choice_id обязательны"}), 400
        user = User.query.filter_by(telegram_id=tg_id).first()
        if not user or not user.run:
            return jsonify({"status": "error", "message": "Нет активной экспедиции"}), 404
        from app.events_parser import process_event_choice
        result = process_event_choice(user.run, event_id, choice_id)
        if result["status"] == "error":
            return jsonify(result), 400
        return jsonify({
            "status": "ok", "next_event": result["next_event"],
            "run": serialize_run(result["run"]),
            "consequences": result.get("consequences"),
        }), 200

    @app.route("/api/next_turn", methods=["POST"])
    def next_turn():
        data = request.get_json(silent=True) or {}
        tg_id, err = _extract_tg_id(data)
        if err:
            return err
        user = User.query.filter_by(telegram_id=tg_id).first()
        if not user or not user.run:
            return jsonify({"status": "error", "message": "Нет активной экспедиции"}), 404
        run = user.run
        if run.current_event_id:
            return jsonify({"status": "error",
                            "message": f"Игрок в ивенте '{run.current_event_id}'"}), 400

        from sqlalchemy.orm.attributes import flag_modified

        # 1. Сезон вперёд
        season_changed = season_mod.advance_season(run)

        # 2. Еда
        _consume_food(run)

        # 3. Витамин C и цинга
        _tick_vitamin_and_scurvy(run, vitamin_used_today=False)

        # 4. День и движение
        run.day += 1
        speed = _calculate_speed(run)
        run.distance_covered += speed

        # 5. Восстановление раненых
        for t in run.travelers:
            if not (t.alive and t.wounded and t.wounded_days_left > 0):
                continue
            t.wounded_days_left -= 1
            if run.inventory.get("herbs", 0) > 0:
                t.wounded_days_left -= 1
                run.inventory["herbs"] -= 1
                if run.inventory["herbs"] <= 0:
                    del run.inventory["herbs"]
                flag_modified(run, "inventory")
            if t.wounded_days_left <= 0:
                t.wounded = False
                t.endurance = max(1, t.endurance_max // 2)
                for c in run.travelers:
                    if c.is_caretaker and c.caring_for == t.name:
                        c.is_caretaker = False
                        c.caring_for = None

        # 6. Титул
        if (run.total_fur_sent >= TITLE_MAGNATE_THRESHOLD
                and run.noble_title != "вельможа"):
            run.noble_title = "вельможа"
        elif (run.total_fur_sent >= TITLE_NOBLE_THRESHOLD
                and not run.noble_title):
            run.noble_title = "дворянин"

        # 7. Пьянство
        if (run.money > DRUNKARD_MONEY_THRESHOLD
                and "drunkard_handled" not in run.tags
                and "drunkard_pending" not in run.tags):
            run.tags.append("drunkard_pending")

        # 8. Достижения
        ach = []
        check_achievements(user, run, ach)
        flag_modified(user, "achievements")

        # 9. Осада
        if run.siege_days_left > 0:
            run.siege_days_left -= 1

        # 10. Смерть
        reason = None
        if run.alive_count <= 0:
            reason = "Отряд погиб."
        elif run.morale <= 0:
            reason = "Отряд взбунтовался и ушёл."
        elif run.hunger_days >= HUNGER_DEATH_DAY:
            reason = "Отряд умер от голода."
        if reason:
            d, dist = run.day, run.distance_covered
            user.total_deaths += 1
            db.session.delete(run)
            db.session.commit()
            return jsonify({"status": "game_over", "reason": reason,
                            "day": d, "distance_covered": dist}), 200

        # 11. Победа
        if run.distance_covered >= 100:
            if "game_won" not in run.tags:
                run.tags.append("game_won")
                flag_modified(run, "tags")
                db.session.commit()
            return jsonify({"status": "victory", "day": run.day,
                            "distance_covered": run.distance_covered}), 200

        # 12. Приоритетные теги
        PRIORITY = {"need_funeral": "event_funeral",
                    "drunkard_pending": "event_drunkard",
                    "healer_pending": "event_healer_visit"}
        prio_id = None
        for tag, eid in PRIORITY.items():
            if tag in run.tags:
                if eid == "event_funeral" and not _has_priest(run):
                    run.tags.remove(tag)
                    flag_modified(run, "tags")
                    continue
                prio_id = eid
                run.tags.remove(tag)
                flag_modified(run, "tags")
                break
        if prio_id:
            run.current_event_id = prio_id
            hint = get_advisor_hint(run)
            db.session.commit()
            return _build_story_event_response(run, prio_id, ach, hint)

        # 13. Сюжет
        sid = _check_story_event(run)
        if sid:
            run.current_event_id = sid
            hint = get_advisor_hint(run)
            flag_modified(run, "tags")
            db.session.commit()
            return _build_story_event_response(run, sid, ach, hint)

        # 14. Обычный ивент
        from app.events_engine import generate_daily_event
        eid = generate_daily_event(run)
        if eid:
            run.current_event_id = eid
        flag_modified(run, "tags")
        hint = get_advisor_hint(run)

        # 15. Сообщение о смене сезона
        season_msg = ""
        if season_changed:
            season_msg = f"\n\nНаступила {season_changed.lower()}."

        db.session.commit()

        if eid:
            return _build_story_event_response(run, eid, ach, hint + season_msg)

        food_spent = run.squad_size * DAILY_FOOD_PER_PERSON
        return jsonify({
            "status": "ok", "type": "quiet_day",
            "message": "День прошёл спокойно. Отряд шёл по тайге." + season_msg,
            "deltas": [f"−{food_spent} провизии"],
            "advisor_hint": hint,
            "achievements": ach,
            "run": serialize_run(run),
        }), 200

    @app.route("/api/do_action", methods=["POST"])
    def do_action():
        data = request.get_json(silent=True) or {}
        tg_id, err = _extract_tg_id(data)
        if err:
            return err
        action_type = data.get("action_type")
        valid = ("wood", "hunt", "fish", "herbs", "pine", "rest",
                 "berries", "sell_fur", "send_to_tsar", "found_city")
        if action_type not in valid:
            return jsonify({"status": "error", "message": "Неизвестное действие"}), 400
        user = User.query.filter_by(telegram_id=tg_id).first()
        if not user or not user.run:
            return jsonify({"status": "error", "message": "Нет активной экспедиции"}), 404
        run = user.run
        if run.current_event_id:
            return jsonify({"status": "error",
                            "message": f"Вы в ивенте '{run.current_event_id}'"}), 400

        import random
        from sqlalchemy.orm.attributes import flag_modified

        # Сезон вперёд
        season_changed = season_mod.advance_season(run)

        # Еда
        _consume_food(run)

        # Витамин (деградация) — до применения эффекта
        vitamin_used = action_type in ("pine", "fish", "berries")
        if not vitamin_used:
            _tick_vitamin_and_scurvy(run, vitamin_used_today=False)

        run.day += 1
        run.warmth = max(0, run.warmth - 5)
        # Зимой тепло падает быстрее
        if run.season == 3:
            run.warmth = max(0, run.warmth - 5)

        # Смерть
        if (run.alive_count <= 0 or run.morale <= 0
                or run.hunger_days >= HUNGER_DEATH_DAY):
            reason = None
            if run.alive_count <= 0:
                reason = "Отряд погиб."
            elif run.morale <= 0:
                reason = "Отряд взбунтовался и ушёл."
            elif run.hunger_days >= HUNGER_DEATH_DAY:
                reason = "Отряд умер от голода."
            d, dist = run.day, run.distance_covered
            user.total_deaths += 1
            db.session.delete(run)
            db.session.commit()
            return jsonify({"status": "game_over", "reason": reason,
                            "day": d, "distance_covered": dist}), 200

        text = ""
        deltas = []

        if action_type == "wood":
            amount = random.randint(3, 7)
            if run.season == 3:  # зимой сухостой мёрзлый
                amount = max(1, amount - 2)
            run.inventory["wood"] = run.inventory.get("wood", 0) + amount
            text = "Отряд рубил сухостой весь день."
            deltas = [f"+{amount} дров"]

        elif action_type == "hunt":
            if run.squad_size < 2:
                text = "Один человек на охоте. Не добытчик."
                deltas = ["Ничего не добыли"]
            else:
                roll = random.random()
                synergy = hunting_synergy(run.squad_size)
                mod = season_mod.get_hunt_modifier(run)
                if roll < 0.5:
                    base = random.randint(*MEAT_PER_DAY)
                    amount = max(1, int(base * synergy * mod))
                    run.meat += amount
                    from app.season import add_vitamin
                    add_vitamin(run, VIT_FROM_MEAT)
                    text = f"Охотились {run.squad_size} человек. Завалили оленя."
                    deltas = [f"+{amount} мяса", f"+{VIT_FROM_MEAT} витамина"]
                elif roll < 0.8:
                    fur_amount = max(1, int(1 * synergy / 2))
                    run.inventory["fur"] = run.inventory.get("fur", 0) + fur_amount
                    text = f"Повезло на пушного зверя."
                    deltas = [f"+{fur_amount} пушнины"]
                else:
                    text = "Зверь ушёл."
                    deltas = ["Ничего не добыли"]

        elif action_type == "fish":
            mod = season_mod.get_fish_modifier(run)
            base = random.randint(*FISH_PER_DAY)
            amount = max(1, int(base * mod))
            run.fish += amount
            from app.season import add_vitamin
            add_vitamin(run, VIT_FROM_FISH)
            text = f"Рыбачили. Улов: {amount}."
            deltas = [f"+{amount} рыбы", f"+{VIT_FROM_FISH} витамина"]

        elif action_type == "berries":
            if not season_mod.can_gather_berries(run):
                text = "Ягоды не растут в это время."
                deltas = []
            else:
                mod = season_mod.get_herbs_modifier(run)
                amount = max(1, int(random.randint(3, 8) * mod))
                run.cranberries = run.cranberries + amount
                from app.season import add_vitamin
                add_vitamin(run, VIT_FROM_BERRIES)
                text = "Собирали ягоды весь день."
                deltas = [f"+{amount} ягод", f"+{VIT_FROM_BERRIES} витамина"]

        elif action_type == "herbs":
            mod = season_mod.get_herbs_modifier(run)
            base = random.randint(1, 4)
            amount = max(1, int(base * mod))
            run.inventory["herbs"] = run.inventory.get("herbs", 0) + amount
            text = "Собирали травы по склонам."
            deltas = [f"+{amount} трав"]

        elif action_type == "pine":
            from app.season import add_vitamin
            add_vitamin(run, VIT_FROM_PINE)
            run.morale = min(100, run.morale + 3)
            text = "Варили горький отвар хвои."
            deltas = [f"+{VIT_FROM_PINE} витамина C", "+3 морали"]

        elif action_type == "rest":
            run.morale = min(100, run.morale + 15)
            run.warmth = min(100, run.warmth + 10)
            text = "День стояли лагерем. Отряд отдохнул."
            deltas = ["+15 морали", "+10 тепла"]
            for t in run.travelers:
                if t.alive and t.wounded and t.wounded_days_left > 0:
                    t.wounded_days_left -= 1
                    if t.wounded_days_left <= 0:
                        t.wounded = False
                        t.endurance = max(1, t.endurance_max // 2)
                        deltas.append(f"Вернулся в строй: {t.name}")
                        for c in run.travelers:
                            if c.is_caretaker and c.caring_for == t.name:
                                c.is_caretaker = False
                                c.caring_for = None

        elif action_type == "sell_fur":
            fur_amount = run.inventory.get("fur", 0)
            if fur_amount <= 0:
                text = "Пушнины нет."
            else:
                price = FUR_PRICE
                if run.cities_count > 0:
                    price = int(price * (1 + 0.1 * run.cities_count))
                revenue = fur_amount * price
                run.money += revenue
                run.inventory["fur"] = 0
                flag_modified(run, "inventory")
                text = f"Продали {fur_amount} пушнины."
                deltas = [f"+{revenue} рублей"]

        elif action_type == "send_to_tsar":
            fur_amount = run.inventory.get("fur", 0)
            if fur_amount < FUR_PER_CHARTER:
                text = f"Нужно минимум {FUR_PER_CHARTER} пушнины."
            else:
                ch = fur_amount // FUR_PER_CHARTER
                spent = ch * FUR_PER_CHARTER
                run.inventory["fur"] = fur_amount - spent
                if run.inventory["fur"] <= 0:
                    del run.inventory["fur"]
                run.charters += ch
                run.total_fur_sent += spent
                flag_modified(run, "inventory")
                text = f"Отправили {spent} пушнины в Москву."
                deltas = [f"+{ch} грамот"]

        elif action_type == "found_city":
            cost = city_charter_cost(run.cities_count)
            if run.charters < cost:
                text = f"Нужно {cost} грамот. У тебя {run.charters}."
            else:
                run.charters -= cost
                run.cities_count += 1
                run.morale = min(100, run.morale + 20)
                text = f"Основан город. Всего: {run.cities_count}."
                deltas = [f"−{cost} грамот", "+20 морали"]

        # Витамин и цинга — после действия, если использовали источник
        if vitamin_used:
            _tick_vitamin_and_scurvy(run, vitamin_used_today=True)

        # Достижения
        ach = []
        check_achievements(user, run, ach)
        flag_modified(user, "achievements")

        food_spent = run.squad_size * DAILY_FOOD_PER_PERSON
        deltas.append(f"−{food_spent} провизии")
        deltas.append("−5 тепла")
        if season_changed:
            deltas.append(f"Наступила {season_changed.lower()}")

        flag_modified(run, "inventory")
        hint = get_advisor_hint(run)
        db.session.commit()

        return jsonify({
            "status": "ok", "type": "action",
            "action_type": action_type,
            "narrative": text, "deltas": deltas,
            "advisor_hint": hint,
            "achievements": ach,
            "run": serialize_run(run),
        }), 200

    @app.route("/api/epilogue", methods=["POST"])
    def epilogue():
        data = request.get_json(silent=True) or {}
        tg_id, err = _extract_tg_id(data)
        if err:
            return err
        user = User.query.filter_by(telegram_id=tg_id).first()
        if not user or not user.run:
            return jsonify({"status": "error", "message": "Нет активной экспедиции"}), 404
        run = user.run
        if "game_won" not in (run.tags or []):
            return jsonify({"status": "error", "message": "Поход ещё не завершён"}), 400
        return jsonify({
            "status": "ok",
            "epilogue": _build_epilogue(run, user),
            "user": serialize_user(user),
            "run": serialize_run(run),
        }), 200
