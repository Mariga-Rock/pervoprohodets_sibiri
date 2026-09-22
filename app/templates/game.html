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
    SEASON_LENGTH, SPEED_BY_SEASON,
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
        logging.basicConfig(
            level=level,
            format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
    if not app.logger.handlers:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s [%(name)s] %(message)s"))
        app.logger.addHandler(h)


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get(
        "SECRET_KEY", "dev-secret-change-me")
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
        return None, (jsonify({"status": "error",
                               "message": "telegram_id обязателен"}), 400)
    if isinstance(tg_id, bool) or not isinstance(tg_id, int):
        return None, (jsonify({"status": "error",
                               "message": "telegram_id должен быть числом"}), 400)
    if tg_id <= 0:
        return None, (jsonify({"status": "error",
                               "message": "telegram_id должен быть положительным"}), 400)
    return tg_id, None


def _extract_username(data):
    username = data.get("username")
    if not isinstance(username, str):
        return None
    return username.strip()[:64] or None


def _has_priest(run):
    return any(t.is_priest and t.alive for t in run.travelers)


def _calculate_speed(run):
    speed = float(SPEED_BY_SEASON.get(run.season, 2))
    if speed <= 0:
        return 0

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
        speed = max(speed, 4.0)

    if run.ermak_wearing_armor:
        speed = max(1.0, speed - 1.0)

    return max(1, int(speed))


def _consume_food(run):
    need = run.squad_size * DAILY_FOOD_PER_PERSON
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
        from app.events_parser import _drop_endurance
        _drop_endurance(run, 1)
    return False


# ============================================================
# МЕДИЦИНА
# ============================================================
def _tick_wounds(run):
    from sqlalchemy.orm.attributes import flag_modified

    for t in run.travelers:
        if not t.alive:
            continue

        if t.lead_poisoning_days > 0:
            t.lead_poisoning_days -= 1
            t.endurance -= 1
            if t.endurance <= 0:
                t.alive = False
                continue

        if t.arrow_stuck:
            t.arrow_days_left -= 1
            if t.arrow_days_left <= 0:
                t.gangrene = True
                t.arrow_stuck = False

        if t.gangrene:
            t.wound_days_left = (t.wound_days_left or 5) - 1
            if t.wound_days_left <= 0:
                t.alive = False
                continue

        if t.infection:
            t.endurance -= 2
            t.wound_days_left = (t.wound_days_left or 5) - 1
            if t.wound_days_left <= 0:
                t.alive = False
                continue

        if t.wound_level > 0 and not t.infection and not t.gangrene:
            t.wound_days_left -= 1
            if run.inventory.get("herbs", 0) > 0:
                t.wound_days_left -= 1
                run.inventory["herbs"] -= 1
                if run.inventory["herbs"] <= 0:
                    del run.inventory["herbs"]
                flag_modified(run, "inventory")

            if t.wound_days_left <= 0:
                if t.wound_level == 3:
                    t.scar = True
                t.wound_level = 0
                t.endurance = max(1, t.endurance_max // 2)

        if (t.wound_level == 2 and not t.infection
                and t.wound_days_left <= 0):
            t.infection = True
            t.wound_days_left = 5

        if (t.wound_level == 3 and not t.gangrene
                and not t.infection
                and t.wound_days_left <= 0):
            t.gangrene = True
            t.wound_days_left = 5


def _tick_scars_and_scurvy(run):
    if not run.scurvy_active:
        return
    from sqlalchemy.orm.attributes import flag_modified
    for t in run.travelers:
        if t.alive and t.scar and t.wound_level == 0:
            t.wound_level = 2
            t.wound_days_left = 3
            t.scar = False
            if "scar_opened" not in run.tags:
                run.tags.append("scar_opened")
                flag_modified(run, "tags")


def _tick_vitamin_and_scurvy(run, vitamin_used_today=False):
    if not vitamin_used_today:
        season_mod.degrade_vit_c(run)

    if (run.days_without_vit >= SCURVY_START_DAYS
            and not run.scurvy_active):
        run.scurvy_active = True
        from app.events_parser import _progress_scurvy
        _progress_scurvy(run)
        _progress_scurvy(run)

    if run.scurvy_active:
        from app.events_parser import _progress_scurvy
        if run.day % 2 == 0:
            _progress_scurvy(run)
        for t in run.travelers:
            if t.alive and t.scurvy:
                t.endurance -= 1
                if t.endurance <= 0:
                    t.alive = False
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


# ============================================================
# СРАВНЕНИЕ С ЕРМАКОМ
# ============================================================
def _milestone_message(run, key):
    if key in (run.milestones_shown or []):
        return None

    expected = {
        "isker": (2, 2),
        "siege": (3, 0),
        "vagai": (4, 2),
    }
    if key not in expected:
        return None

    exp_year, exp_season = expected[key]
    cur_year, cur_season = run.year, run.season

    ms = list(run.milestones_shown or [])
    ms.append(key)
    run.milestones_shown = ms

    titles = {"isker": "Искер", "siege": "Осада Карачи", "vagai": "Вагай"}
    title = titles.get(key, key)

    if cur_year == exp_year and cur_season == exp_season:
        return (f"⏳ {title}: вы здесь примерно тогда же, когда "
                f"Ермак Тимофеевич. {cur_year}-й год, "
                f"{season_mod.season_name(run).lower()}.")
    if cur_year < exp_year or (cur_year == exp_year
                                and cur_season < exp_season):
        return (f"⚡ {title}: вы достигли быстрее, чем Ермак Тимофеевич. "
                f"Он был здесь в {exp_year}-й год, осенью. "
                f"Вы — в {cur_year}-й год.")
    return (f"🌫 {title}: вы блуждаете по тайге. "
            f"Ермак Тимофеевич уже достиг этого места — "
            f"{exp_year}-й год, осень. Вы отстали.")


# ============================================================
# СЮЖЕТНЫЕ ТРИГГЕРЫ
# ============================================================
def _check_story_event(run):
    import random
    from sqlalchemy.orm.attributes import flag_modified

    # ---- ОСАДА ----
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

    # ---- СЛУХИ О ЛЮДОЕДСТВЕ ----
    if (run.cannibal_day > 0
            and run.day - run.cannibal_day >= 10
            and "cannibal_rumors_done" not in run.tags):
        run.tags.append("cannibal_rumors_done")
        flag_modified(run, "tags")
        return "event_cannibal_rumors"

    # ---- СТРЕЛА В ТЕЛЕ ----
    arrow_stuck = any(t.alive and t.arrow_stuck for t in run.travelers)
    if arrow_stuck and "arrow_event_done" not in run.tags:
        run.tags.append("arrow_event_done")
        flag_modified(run, "tags")
        return "event_arrow_wound"

    # ---- ГАНГРЕНА ----
    has_gangrene = any(t.alive and t.gangrene for t in run.travelers)
    if has_gangrene and "gangrene_event_done" not in run.tags:
        run.tags.append("gangrene_event_done")
        flag_modified(run, "tags")
        return "event_gangrene_wound"

    # ---- ЦИНГА (первый раз) ----
    if run.scurvy_active and "scurvy_event_done" not in run.tags:
        run.tags.append("scurvy_event_done")
        flag_modified(run, "tags")
        return "event_scurvy_start"

    # ---- ЦИНГА (повторное лечение) ----
    if (run.scurvy_active
            and "scurvy_event_done" in run.tags
            and run.day % 3 == 0
            and f"scurvy_treat_{run.day}" not in run.tags):
        run.tags.append(f"scurvy_treat_{run.day}")
        flag_modified(run, "tags")
        return "event_scurvy_treatment"

    # ---- СЛУХ 1 ----
    if run.distance_covered >= 10 and "rumor_1_done" not in run.tags:
        run.tags.append("rumor_1_done")
        flag_modified(run, "tags")
        return "event_first_rumor"

    # ---- ЧУВАШСКИЙ МЫС (2-й год) ----
    if (run.distance_covered >= 25 and run.isker_status == "none"
            and run.year >= 2):
        return "event_chuvash_mys"

    # ---- УКРЕПЛЕНИЕ ИСКЕРА ----
    if (run.isker_status == "taken"
            and "isker_fortified" not in run.tags):
        run.tags.append("isker_fortified")
        flag_modified(run, "tags")
        return "event_fortify_isker"

    # ---- СЛУХ 2 ----
    if (run.distance_covered >= 35 and run.mangazeya_rumors >= 1
            and "rumor_2_done" not in run.tags):
        run.tags.append("rumor_2_done")
        flag_modified(run, "tags")
        return "event_second_rumor"

    # ---- НАЧАЛО ОСАДЫ (3-й год) ----
    if (run.isker_status == "taken"
            and run.distance_covered >= 45
            and run.year >= 3
            and "siege_started" not in run.tags):
        run.siege_days_left = random.randint(10, 15)
        run.isker_status = "under_siege"
        run.tags.append("siege_started")
        flag_modified(run, "tags")
        return "event_siege_start"

    # ---- ЯСАК СОБРАН ----
    if run.yasak_count >= 5 and "yasak_triggered" not in run.tags:
        run.tags.append("yasak_triggered")
        flag_modified(run, "tags")
        return "event_yasak_sent"

    # ---- ДАР ЦАРЯ ----
    if "yasak_sent" in run.tags and "tsar_gift_done" not in run.tags:
        run.tags.append("tsar_gift_done")
        flag_modified(run, "tags")
        return "event_tsar_gift"

    # ---- ПОДСКАЗКА О ПАНЦИРЕ ----
    if ("tsar_gift_done" in run.tags
            and "armor_warning_done" not in run.tags
            and run.ermak_has_armor):
        run.tags.append("armor_warning_done")
        flag_modified(run, "tags")
        return "event_old_kazak_warning"

    # ---- СЕЛЬКУПЫ: БУНТ ----
    if ("selkup_risky" in run.tags
            and "selkup_revolt_done" not in run.tags):
        if random.random() < 0.15:
            run.tags.append("selkup_revolt_done")
            flag_modified(run, "tags")
            return "event_selkup_revolt"

    # ---- БЕЛЫЙ МЕДВЕДЬ ----
    food_total = (run.flour or 0) + (run.fish or 0) + (run.meat or 0)
    if (run.distance_covered >= 80
            and run.season == 3
            and food_total < run.squad_size * 2
            and "polar_bear_done" not in run.tags):
        run.tags.append("polar_bear_done")
        flag_modified(run, "tags")
        return "event_polar_bear"

    # ---- ГИПЕРВИТАМИНОЗ ----
    if (run.hypervitaminosis_active
            and "hypervitaminosis_event_done" not in run.tags):
        run.tags.append("hypervitaminosis_event_done")
        flag_modified(run, "tags")
        return "event_hypervitaminosis"

    # ---- ВОЛХОВСКИЙ ----
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

    # ---- ВАГАЙ (4-й год) ----
    if (run.distance_covered >= 90 and run.year >= 4
            and "vagai_done" not in run.tags):
        run.tags.append("vagai_done")
        flag_modified(run, "tags")
        if run.ermak_wearing_armor:
            return "event_vagai_night_armor"
        return "event_vagai_night"

    # ---- САМОЯДЬ ----
    if run.distance_covered >= 95 and "samoyed_done" not in run.tags:
        run.tags.append("samoyed_done")
        flag_modified(run, "tags")
        return "event_samoyed_camp"

    # ---- ЗЕМЛЯ МАНГАЗЕЙСКАЯ ----
    if run.distance_covered >= 100 and "mangazeya_done" not in run.tags:
        run.tags.append("mangazeya_done")
        flag_modified(run, "tags")
        return "event_mangazeya_land"

    return None


def _build_story_event_response(run, event_id, ach, hint):
    from app.events_loader import get_event as load_event
    ed = load_event(event_id)
    if not ed:
        return jsonify({
            "status": "ok", "type": "quiet_day",
            "message": "Тихий день.",
            "advisor_hint": hint,
            "achievements": ach,
            "run": serialize_run(run),
        }), 200
    choices = [{"choice_id": ch["choice_id"], "text": ch["text"],
                "conditions": ch.get("conditions") or {}}
               for ch in ed.get("choices", [])]

    milestone = None
    if event_id == "event_chuvash_mys":
        milestone = _milestone_message(run, "isker")
    elif event_id == "event_siege_start":
        milestone = _milestone_message(run, "siege")
    elif event_id in ("event_vagai_night", "event_vagai_night_armor"):
        milestone = _milestone_message(run, "vagai")

    text = ed.get("text") or "Ничего не произошло."
    if milestone:
        text = milestone + "\n\n" + text

    return jsonify({
        "status": "ok", "type": "event",
        "event_id": event_id,
        "event_title": ed.get("title", ""),
        "event_text": text,
        "choices": choices,
        "advisor_hint": hint,
        "achievements": ach,
        "run": serialize_run(run),
    }), 200


# ============================================================
# ЭПИЛОГ
# ============================================================
def _build_epilogue(run, user):
    lines = []
    lines.append(f"Вы прошли {run.distance_covered} вёрст за {run.day} дней "
                 f"({run.year} лет).")

    alive = [t for t in run.travelers if t.alive]
    dead = [t for t in run.travelers if not t.alive]
    if dead:
        lines.append(f"Погибли: {len(dead)}. "
                     f"Погибшие: " + ", ".join(t.name for t in dead) + ".")
    scarred = [t for t in alive if t.scar]
    if scarred:
        lines.append("Остались со шрамами: "
                     + ", ".join(t.name for t in scarred) + ".")

    if "isker_garrison" in run.tags:
        lines.append("Искер взят и укреплён гарнизоном. "
                     "Первый русский острог на Иртыше.")
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
        lines.append("Пять племён признали руку московского царя. "
                     "Ясак отправлен в Москву.")
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
        if run.ermak_wearing_armor:
            lines.append("Ермак Тимофеевич погиб так же, как в реальности. "
                         "Тяжёлый панцирь утянул его на дно. "
                         "История повторилась.")
        else:
            lines.append("Ермак Тимофеевич погиб на Вагае. "
                         "Отряд вёл Матвей Мещеряк.")

    if run.noble_title:
        lines.append(f"Царь пожаловал титул: {run.noble_title}.")

    if run.cannibal_day > 0:
        if "cannibal_admitted" in (run.tags or []):
            lines.append("Отряд ел мёртвых. Признали вину, принесли дары. "
                         "Племена не простили, но говорить будут.")
        elif "cannibal_executed" in (run.tags or []):
            lines.append("Отряд ел мёртвых. Виновного казнили. "
                         "Племена приняли ответ. Тень осталась.")
        else:
            lines.append("Отряд ел мёртвых. Племена это помнят. "
                         "Ясак собрать почти не удалось.")

    if "ate_polar_liver" in (run.tags or []):
        lines.append("Отряд ел печень белого медведя. "
                     "Гипервитаминоз A убил многих. "
                     "Местные знали об этой опасности. Вы не послушали.")
    elif "polar_bear_done" in (run.tags or []):
        lines.append("Проводник сказал: злой дух в печени. Вы поверили. "
                     "Это спасло отряд.")

    # Крещёные племена
    baptized = []
    if "baptized_tatar" in (run.tags or []):
        baptized.append("татары")
    if "baptized_vogul" in (run.tags or []):
        baptized.append("вогулы")
    if "baptized_ostyak" in (run.tags or []):
        baptized.append("остяки")
    if "baptized_selkup" in (run.tags or []):
        baptized.append("селькупы")
    if "baptized_samoyed" in (run.tags or []):
        baptized.append("самоядь")
    if baptized:
        lines.append("Крещение приняли: " + ", ".join(baptized) + ".")

    # Праздники
    christmases = run.christmas_years or []
    easters = run.easter_years or []
    if christmases or easters:
        parts = []
        if christmases:
            parts.append(f"Рождество — {len(christmases)} раз")
        if easters:
            parts.append(f"Пасха — {len(easters)} раз")
        lines.append("Отряд праздновал: " + ", ".join(parts) + ".")

    final = ("В 1601 году, через шестнадцать лет после вашего похода, "
             "на реке Таз воеводы Мирон Шаховской и Данила Хрипунов "
             "основали город Мангазея. Ваше открытие стало первым шагом. "
             "Сибирь помнит вас.")
    return {"headline": "Земля мангазейская", "lines": lines, "final": final}


# ============================================================
# СЕРИАЛИЗАЦИЯ
# ============================================================
def serialize_run(run):
    return {
        "day": run.day,
        "year": run.year,
        "season": run.season,
        "season_day": run.season_day,
        "season_name": season_mod.season_name(run),
        "is_winter": run.season == 3,
        "distance_covered": run.distance_covered,
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
        "ermak_has_armor": run.ermak_has_armor,
        "ermak_wearing_armor": run.ermak_wearing_armor,
        "armor_warning_given": run.armor_warning_given,
        "cannibal_day": run.cannibal_day,
        "ate_polar_liver_day": run.ate_polar_liver_day,
        "hypervitaminosis_active": run.hypervitaminosis_active,
        "christmas_years": run.christmas_years or [],
        "easter_years": run.easter_years or [],
        "travelers": [
            {"id": t.id, "name": t.name, "hunting": t.hunting,
             "endurance": t.endurance, "endurance_max": t.endurance_max,
             "is_ataman": t.is_ataman, "is_doctor": t.is_doctor,
             "is_priest": t.is_priest,
             "wound_level": t.wound_level or 0,
             "wound_days_left": t.wound_days_left or 0,
             "infection": t.infection,
             "gangrene": t.gangrene,
             "scar": t.scar,
             "lead_poisoning_days": t.lead_poisoning_days or 0,
             "arrow_stuck": t.arrow_stuck,
             "arrow_days_left": t.arrow_days_left or 0,
             "wounded": t.wounded,
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
                                    "message": "не удалось создать"}), 500
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
            user_id=user.id,
            day=DEFAULT_DAY, year=1, season=2, season_day=1,
            distance_covered=DEFAULT_DISTANCE,
            flour=DEFAULT_FLOUR, fish=DEFAULT_FISH,
            meat=DEFAULT_MEAT, cranberries=DEFAULT_CRANBERRIES,
            vit_c=DEFAULT_VIT_C, morale=DEFAULT_MORALE,
            warmth=DEFAULT_WARMTH, inventory=dict(DEFAULT_INVENTORY),
            tags=[], recent_events=[], milestones_shown=[],
            christmas_years=[], easter_years=[],
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
                alive=True, wound_level=0,
            )
            db.session.add(t)

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return jsonify({"status": "error",
                            "message": "не удалось создать"}), 500
        return _state_response("created", user, new_run)

    @app.route("/api/get_event", methods=["POST"])
    def get_event():
        data = request.get_json(silent=True) or {}
        tg_id, err = _extract_tg_id(data)
        if err:
            return err
        event_id = data.get("event_id")
        if not event_id:
            return jsonify({"status": "error",
                            "message": "event_id обязателен"}), 400
        user = User.query.filter_by(telegram_id=tg_id).first()
        if not user or not user.run:
            return jsonify({"status": "error",
                            "message": "Нет активной экспедиции"}), 404
        run = user.run
        if run.current_event_id != event_id:
            return jsonify({"status": "error",
                            "message": f"Игрок в '{run.current_event_id}'"}), 400
        from app.events_loader import get_event as load_event
        ed = load_event(event_id)
        if not ed:
            return jsonify({"status": "error",
                            "message": f"Ивент '{event_id}' не найден"}), 404
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
            return jsonify({"status": "error",
                            "message": "event_id и choice_id обязательны"}), 400
        user = User.query.filter_by(telegram_id=tg_id).first()
        if not user or not user.run:
            return jsonify({"status": "error",
                            "message": "Нет активной экспедиции"}), 404
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
            return jsonify({"status": "error",
                            "message": "Нет активной экспедиции"}), 404
        run = user.run
        if run.current_event_id:
            return jsonify({"status": "error",
                            "message": f"Игрок в ивенте '{run.current_event_id}'"}), 400

        from sqlalchemy.orm.attributes import flag_modified

        season_changed = season_mod.advance_season(run)
        _consume_food(run)
        _tick_vitamin_and_scurvy(run, vitamin_used_today=False)

        run.day += 1
        speed = _calculate_speed(run)
        run.distance_covered += speed
        winter_stop = (speed == 0)

        _tick_wounds(run)
        _tick_scars_and_scurvy(run)

        # Гипервитаминоз
        if run.ate_polar_liver_day > 0 and not run.hypervitaminosis_active:
            if run.day - run.ate_polar_liver_day >= 2:
                run.hypervitaminosis_active = True
                run.hypervitaminosis_days = 5
        if run.hypervitaminosis_active:
            import random as _r
            candidates = [t for t in run.travelers
                          if t.alive and t.endurance > 1]
            if candidates:
                t = _r.choice(candidates)
                t.endurance -= 1
            run.hypervitaminosis_days -= 1
            if run.hypervitaminosis_days <= 0:
                run.hypervitaminosis_active = False

        # Титул
        if (run.total_fur_sent >= TITLE_MAGNATE_THRESHOLD
                and run.noble_title != "вельможа"):
            run.noble_title = "вельможа"
        elif (run.total_fur_sent >= TITLE_NOBLE_THRESHOLD
                and not run.noble_title):
            run.noble_title = "дворянин"

        # Пьянство
        if (run.money > DRUNKARD_MONEY_THRESHOLD
                and "drunkard_handled" not in run.tags
                and "drunkard_pending" not in run.tags):
            run.tags.append("drunkard_pending")

        ach = []
        check_achievements(user, run, ach)
        flag_modified(user, "achievements")

        if run.siege_days_left > 0:
            run.siege_days_left -= 1

        # Смерть
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

        # Победа
        if run.distance_covered >= 100:
            if "game_won" not in run.tags:
                run.tags.append("game_won")
                flag_modified(run, "tags")
                db.session.commit()
            return jsonify({"status": "victory", "day": run.day,
                            "distance_covered": run.distance_covered}), 200

        # Приоритетные
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
            from app.events_loader import get_event as _ge
            if _ge(prio_id):
                run.current_event_id = prio_id
                hint = get_advisor_hint(run)
                db.session.commit()
                return _build_story_event_response(run, prio_id, ach, hint)

        # Сюжетные
        sid = _check_story_event(run)
        if sid:
            from app.events_loader import get_event as _ge
            if _ge(sid):
                run.current_event_id = sid
                hint = get_advisor_hint(run)
                flag_modified(run, "tags")
                db.session.commit()
                return _build_story_event_response(run, sid, ach, hint)

        # Обычный ивент
        from app.events_engine import generate_daily_event
        eid = generate_daily_event(run)
        if eid:
            from app.events_loader import get_event as _ge
            if not _ge(eid):
                eid = None
            else:
                run.current_event_id = eid
        flag_modified(run, "tags")
        hint = get_advisor_hint(run)

        season_msg = ""
        if season_changed:
            season_msg = "\n\n" + season_changed

        db.session.commit()

        if eid:
            return _build_story_event_response(run, eid, ach, hint + season_msg)

        food_spent = run.squad_size * DAILY_FOOD_PER_PERSON
        if winter_stop:
            message = "Зима. Отряд стоит лагерем. Идти нельзя — мороз и снег."
        else:
            message = "День прошёл спокойно. Отряд шёл по тайге."
        return jsonify({
            "status": "ok", "type": "quiet_day",
            "message": message + season_msg,
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
                 "berries", "sell_fur", "send_to_tsar", "found_city",
                 "toggle_armor", "christmas", "easter")
        if action_type not in valid:
            return jsonify({"status": "error",
                            "message": "Неизвестное действие"}), 400
        user = User.query.filter_by(telegram_id=tg_id).first()
        if not user or not user.run:
            return jsonify({"status": "error",
                            "message": "Нет активной экспедиции"}), 404
        run = user.run
        if run.current_event_id:
            return jsonify({"status": "error",
                            "message": f"Вы в ивенте '{run.current_event_id}'"}), 400

        import random
        from sqlalchemy.orm.attributes import flag_modified

        # Снять/надеть панцирь — не тратит день
        if action_type == "toggle_armor":
            if not run.ermak_has_armor:
                return jsonify({"status": "error",
                                "message": "У Ермака нет панциря."}), 400
            if run.ermak_wearing_armor:
                run.ermak_wearing_armor = False
                text = "Ермак снял панцирь. Идти легче."
            else:
                run.ermak_wearing_armor = True
                text = "Ермак надел панцирь. От стрелы спасёт."
            db.session.commit()
            return jsonify({
                "status": "ok", "type": "action",
                "action_type": "toggle_armor",
                "narrative": text, "deltas": [],
                "run": serialize_run(run),
            }), 200

        # Рождество
        if action_type == "christmas":
            if run.season != 3:
                return jsonify({"status": "error",
                                "message": "Рождество только зимой."}), 400
            if run.season_day != 3:
                return jsonify({"status": "error",
                                "message": "Рождество празднуется на третий день зимы."}), 400
            years = list(run.christmas_years or [])
            if run.year in years:
                return jsonify({"status": "error",
                                "message": "Рождество уже отпраздновано."}), 400
            if not _has_priest(run):
                return jsonify({"status": "error",
                                "message": "Без священника службы нет."}), 400

            _consume_food(run)
            run.day += 1
            run.warmth = max(0, run.warmth - 3)
            run.morale = min(100, run.morale + 25)
            run.discipline = min(100, run.discipline + 5)
            run.flour = max(0, run.flour - 20)
            run.meat = max(0, run.meat - 2)
            run.vit_c = min(100, run.vit_c + 10)

            years.append(run.year)
            run.christmas_years = years
            flag_modified(run, "christmas_years")

            ach = []
            check_achievements(user, run, ach)
            flag_modified(user, "achievements")

            text = ("Отец Никифор служит торжественную службу. "
                    "Свечи горят. Певчие поют «Рождество Твое, Христе Боже наш». "
                    "На столах — что Бог послал: солёное мясо, хлеб, клюква.")
            deltas = ["+25 морали", "+5 дисциплины", "+10 витамина C",
                      "−20 муки", "−2 мяса"]
            db.session.commit()
            return jsonify({
                "status": "ok", "type": "action",
                "action_type": "christmas",
                "narrative": text, "vignette": "christmas",
                "deltas": deltas, "advisor_hint": None,
                "achievements": ach, "run": serialize_run(run),
            }), 200

        # Пасха
        if action_type == "easter":
            if run.season != 0:
                return jsonify({"status": "error",
                                "message": "Пасха только весной."}), 400
            if run.season_day != 4:
                return jsonify({"status": "error",
                                "message": "Пасха празднуется на четвёртый день весны."}), 400
            years = list(run.easter_years or [])
            if run.year in years:
                return jsonify({"status": "error",
                                "message": "Пасха уже отпразднована."}), 400
            if not _has_priest(run):
                return jsonify({"status": "error",
                                "message": "Без священника службы нет."}), 400

            _consume_food(run)
            run.day += 1
            run.warmth = max(0, run.warmth - 2)
            run.morale = min(100, run.morale + 30)
            run.discipline = min(100, run.discipline + 5)
            run.flour = max(0, run.flour - 20)
            run.meat = max(0, run.meat - 2)
            run.vit_c = min(100, run.vit_c + 15)

            years.append(run.year)
            run.easter_years = years
            flag_modified(run, "easter_years")

            ach = []
            check_achievements(user, run, ach)
            flag_modified(user, "achievements")

            # Крещение — если есть присягнувшие
            oath_tags = ("tatar_oath", "vogul_oath", "ostyak_oath",
                         "selkup_oath", "samoyed_oath")
            has_oath = any(t in (run.tags or []) for t in oath_tags)
            if has_oath:
                run.current_event_id = "event_easter_baptism"

            text = ("Отец Никифор служит пасхальную заутреню. "
                    "Певчие поют «Христос воскресе из мертвых». "
                    "На столах — куличи из последней муки, крашеные яйца. "
                    "Отряд обнимается. Христос воскресе!")
            deltas = ["+30 морали", "+5 дисциплины", "+15 витамина C",
                      "−20 муки", "−2 мяса"]
            db.session.commit()
            return jsonify({
                "status": "ok", "type": "action",
                "action_type": "easter",
                "narrative": text, "vignette": "easter",
                "deltas": deltas, "advisor_hint": None,
                "achievements": ach, "run": serialize_run(run),
            }), 200

        # Зимой нельзя в тайгу
        if run.season == 3 and action_type in ("wood", "hunt", "fish",
                                                "herbs", "berries"):
            return jsonify({
                "status": "error",
                "message": "Зимой в тайге делать нечего. Отряд сидит у костра.",
            }), 400

        season_changed = season_mod.advance_season(run)
        _consume_food(run)

        vitamin_used = action_type in ("pine", "fish", "berries")
        if not vitamin_used:
            _tick_vitamin_and_scurvy(run, vitamin_used_today=False)

        run.day += 1
        run.warmth = max(0, run.warmth - 5)
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
            if run.season == 3:
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
                base = random.randint(*MEAT_PER_DAY)
                amount = max(1, int(base * synergy * mod))
                has_salt = run.inventory.get("salt", 0) > 0

                if roll < 0.6:
                    run.meat += amount
                    from app.season import add_vitamin
                    add_vitamin(run, VIT_FROM_MEAT)
                    text = "Чистое попадание. Мясо хорошее."
                    deltas = [f"+{amount} мяса", f"+{VIT_FROM_MEAT} витамина"]
                elif roll < 0.8:
                    if has_salt:
                        run.inventory["salt"] -= 1
                        if run.inventory["salt"] <= 0:
                            del run.inventory["salt"]
                        run.meat += amount
                        text = "Пуля в кость. Свинец вырезали, мясо промыли солью."
                        deltas = [f"+{amount} мяса", "−1 соли"]
                    else:
                        run.meat += amount
                        if "lead_meat" not in run.tags:
                            run.tags.append("lead_meat")
                        text = "Пуля в кость. Свинец в мясе. Соли нет."
                        deltas = [f"+{amount} мяса", "Мясо со свинцом"]
                elif roll < 0.95:
                    half = max(1, amount // 2)
                    if has_salt:
                        run.inventory["salt"] -= 1
                        if run.inventory["salt"] <= 0:
                            del run.inventory["salt"]
                        run.meat += half
                        text = "Пуля в живот. Выпотрошили, промыли солью."
                        deltas = [f"+{half} мяса", "−1 соли"]
                    else:
                        run.meat += half
                        if "rotten_meat" not in run.tags:
                            run.tags.append("rotten_meat")
                        text = "Пуля в живот. ЖКТ разорван. Мясо протухнет."
                        deltas = [f"+{half} мяса", "Мясо протухнет"]
                else:
                    text = "Промах. Зверь ушёл."
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
                if t.alive and t.wound_level > 0 and t.wound_days_left > 0:
                    t.wound_days_left -= 1
                    if t.wound_days_left <= 0:
                        if t.wound_level == 3:
                            t.scar = True
                        t.wound_level = 0
                        t.endurance = max(1, t.endurance_max // 2)
                        deltas.append(f"Вернулся в строй: {t.name}")

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

        if vitamin_used:
            _tick_vitamin_and_scurvy(run, vitamin_used_today=True)

        _tick_wounds(run)
        _tick_scars_and_scurvy(run)

        ach = []
        check_achievements(user, run, ach)
        flag_modified(user, "achievements")

        food_spent = run.squad_size * DAILY_FOOD_PER_PERSON
        deltas.append(f"−{food_spent} провизии")
        deltas.append("−5 тепла")
        if season_changed:
            deltas.append(season_changed)

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
            return jsonify({"status": "error",
                            "message": "Нет активной экспедиции"}), 404
        run = user.run
        if "game_won" not in (run.tags or []):
            return jsonify({"status": "error",
                            "message": "Поход ещё не завершён"}), 400
        return jsonify({
            "status": "ok",
            "epilogue": _build_epilogue(run, user),
            "user": serialize_user(user),
            "run": serialize_run(run),
        }), 200
