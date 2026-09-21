"""Парсер ивентов."""
import random

from sqlalchemy.orm.attributes import flag_modified

from app.extensions import db
from app.events_loader import get_event
from app.constants import (MAX_VIT_C, MAX_MORALE, MAX_WARMTH)


_ITEM_NAMES = {
    "wood": "дров", "herbs": "трав", "salt": "соли",
    "salted_meat": "солёного мяса", "raw_meat": "сырого мяса",
    "fish": "рыбы", "fur": "пушнины", "money": "серебра",
    "lancet": "ланцетов", "silver_cross": "серебряных крестов",
    "bear_skin": "медвежьих шкур", "wolf_skin": "волчьих шкур",
    "wolf_cub": "волчат", "dog_sled": "собачьих упряжек",
}


# Разрешённые флаги и их типы для set_flags.
_FLAG_TYPES = {
    "isker_status": str,
    "siege_days_left": int,
    "siege_result": str,
    "ivan_koltso_alive": bool,
    "ermak_alive": bool,
    "leader": str,
    "mangazeya_rumors": int,
    "yasak_count": int,
    "volhovsky_arrived": bool,
    "volhovsky_alive": bool,
    "volhovsky_healed": bool,
    "noble_title": str,
}


def _progress_scurvy(run):
    healthy = [t for t in run.travelers
               if t.alive and not t.scurvy and not t.wounded]
    if not healthy:
        return None
    t = random.choice(healthy)
    t.scurvy = True
    return t.name


def _has_doctor(run):
    return any(t.is_doctor and t.alive and not t.wounded and not t.is_caretaker
               for t in run.travelers)


def _pick_caretaker(run, exclude_name):
    candidates = [t for t in run.travelers
                  if t.alive and not t.wounded and not t.is_caretaker
                  and t.name != exclude_name]
    return random.choice(candidates) if candidates else None


def _wound_random_traveler(run):
    healthy = [t for t in run.travelers
               if t.alive and not t.wounded and not t.is_caretaker]
    if healthy:
        t = random.choice(healthy)
        t.endurance -= 1
        if t.endurance <= 0:
            t.wounded = True
            days = 3 if _has_doctor(run) else 5
            caretaker = _pick_caretaker(run, t.name)
            if caretaker:
                caretaker.is_caretaker = True
                caretaker.caring_for = t.name
                t.wounded_days_left = days
            else:
                t.wounded_days_left = days * 2
            return ("wound", t.name)
        return (None, t.name)

    wounded = [t for t in run.travelers if t.alive and t.wounded]
    if wounded:
        t = random.choice(wounded)
        if random.random() < 0.9:
            t.alive = False
            for c in run.travelers:
                if c.is_caretaker and c.caring_for == t.name:
                    c.is_caretaker = False
                    c.caring_for = None
            return ("death", t.name)
        t.endurance = 1
        return (None, t.name)
    return None


def _snapshot_run(run):
    return {
        "vit_c": run.vit_c, "morale": run.morale,
        "warmth": run.warmth, "discipline": run.discipline,
        "money": run.money, "charters": run.charters,
        "flour": run.flour, "fish": run.fish, "meat": run.meat,
        "inventory": dict(run.inventory),
        "travelers": [
            {"name": t.name, "endurance": t.endurance,
             "wounded": t.wounded, "scurvy": t.scurvy,
             "is_caretaker": t.is_caretaker, "alive": t.alive}
            for t in run.travelers
        ],
    }


def _build_consequences(snap_before, run, choice_data):
    deltas = []
    stat_names = {
        "vit_c": "Витамин C", "morale": "Мораль",
        "warmth": "Тепло", "discipline": "Дисциплина",
        "money": "Рублей", "charters": "Грамот",
    }
    for field, name in stat_names.items():
        if field not in snap_before:
            continue
        before = snap_before[field]
        after = getattr(run, field, None)
        if after is None or before == after:
            continue
        d = after - before
        sign = "+" if d > 0 else "−"
        deltas.append(f"{sign}{abs(d)} {name}")

    for field, name in (("flour", "муки"), ("fish", "рыбы"), ("meat", "мяса")):
        before = snap_before.get(field, 0)
        after = getattr(run, field, 0)
        if before != after:
            d = after - before
            sign = "+" if d > 0 else "−"
            deltas.append(f"{sign}{abs(d)} {name}")

    items = set(snap_before["inventory"].keys()) | set(run.inventory.keys())
    for item in sorted(items):
        before = snap_before["inventory"].get(item, 0)
        after = run.inventory.get(item, 0)
        if before != after:
            d = after - before
            sign = "+" if d > 0 else "−"
            name = _ITEM_NAMES.get(item, item)
            deltas.append(f"{sign}{abs(d)} {name}")

    before_map = {t["name"]: t for t in snap_before["travelers"]}
    for t in run.travelers:
        b = before_map.get(t.name)
        if not b:
            continue
        if b["alive"] and not t.alive:
            deltas.append(f"☠ Погиб: {t.name}")
        elif not b["wounded"] and t.wounded:
            deltas.append(f"🩹 Ранен: {t.name}")
        elif b["wounded"] and not t.wounded and t.alive:
            deltas.append(f"💚 Вернулся в строй: {t.name}")
        elif not b.get("scurvy") and t.scurvy:
            deltas.append(f"🫐 Цинга у: {t.name}")
        elif b.get("scurvy") and not t.scurvy:
            deltas.append(f"💚 Излечился: {t.name}")
        elif not b.get("is_caretaker") and t.is_caretaker:
            deltas.append(f"Остался с раненым: {t.name}")
        elif b.get("is_caretaker") and not t.is_caretaker:
            deltas.append(f"Освободился: {t.name}")
        elif b["endurance"] != t.endurance and t.alive and not t.wounded:
            if t.endurance < b["endurance"]:
                deltas.append(f"Вымотан: {t.name}")

    narrative = choice_data.get("consequences") or \
                f"Вы выбрали: {choice_data.get('text', '')}."
    return {"narrative": narrative, "deltas": deltas}


def _apply_stats(run, stats_diff):
    if not stats_diff:
        return
    cure_flag = stats_diff.pop("cure_scurvy", 0)
    if "vit_c" in stats_diff:
        run.vit_c = max(0, min(run.vit_c + stats_diff["vit_c"], MAX_VIT_C))
    if "morale" in stats_diff:
        run.morale = max(0, min(run.morale + stats_diff["morale"], MAX_MORALE))
    if "warmth" in stats_diff:
        run.warmth = max(0, min(run.warmth + stats_diff["warmth"], MAX_WARMTH))
    if "discipline" in stats_diff:
        run.discipline = max(0, min(run.discipline + stats_diff["discipline"], 100))
    if "flour" in stats_diff:
        run.flour = max(0, run.flour + stats_diff["flour"])
    if "fish" in stats_diff:
        run.fish = max(0, run.fish + stats_diff["fish"])
    if "meat" in stats_diff:
        run.meat = max(0, run.meat + stats_diff["meat"])
    if "cranberries" in stats_diff:
        run.cranberries = max(0, run.cranberries + stats_diff["cranberries"])
    if "money" in stats_diff:
        run.money = max(0, run.money + stats_diff["money"])
    if "charters" in stats_diff:
        run.charters = max(0, run.charters + stats_diff["charters"])
    if "endurance" in stats_diff and stats_diff["endurance"] < 0:
        for _ in range(abs(stats_diff["endurance"])):
            _wound_random_traveler(run)
    if cure_flag:
        sick = [t for t in run.travelers if t.alive and t.scurvy]
        for t in sick[:cure_flag]:
            t.scurvy = False
            t.scurvy_refused = False
            t.scurvy_healer_seen = False


def _apply_flags(run, flags):
    if not flags:
        return
    for key, value in flags.items():
        expected = _FLAG_TYPES.get(key)
        if expected is None:
            continue
        try:
            if expected is bool:
                setattr(run, key, bool(value))
            elif expected is int:
                setattr(run, key, int(value))
            elif expected is str:
                setattr(run, key, str(value))
        except (TypeError, ValueError):
            continue


def _apply_tags(run, tags_to_add):
    if not tags_to_add:
        return
    for tag in tags_to_add:
        if tag not in run.tags:
            run.tags.append(tag)


def _apply_inventory(run, items_add, items_remove):
    if items_remove:
        for item in items_remove:
            if item in run.inventory:
                run.inventory[item] -= 1
                if run.inventory[item] <= 0:
                    del run.inventory[item]
    if items_add:
        for item, qty in items_add.items():
            run.inventory[item] = run.inventory.get(item, 0) + qty


def _check_conditions(run, conditions):
    if not conditions:
        return True, None
    required = conditions.get("items_required") or {}
    for item, qty in required.items():
        if run.inventory.get(item, 0) < qty:
            return False, f"Не хватает предмета: {item}"
    for tag in conditions.get("tags_required") or []:
        if tag not in run.tags:
            return False, f"Не хватает условия: {tag}"
    for stat, min_val in (conditions.get("stats_min") or {}).items():
        if getattr(run, stat, 0) < min_val:
            return False, f"Слишком низкий {stat}"
    for stat, max_val in (conditions.get("stats_max") or {}).items():
        if getattr(run, stat, 0) > max_val:
            return False, f"Слишком высокий {stat}"
    return True, None


def process_event_choice(run, event_id, choice_id):
    if run.current_event_id != event_id:
        return {"status": "error",
                "message": f"Рассинхронизация: '{run.current_event_id}' vs '{event_id}'"}
    event_data = get_event(event_id)
    if not event_data:
        return {"status": "error", "message": f"Ивент '{event_id}' не найден"}

    choice_data = next((ch for ch in event_data["choices"]
                        if ch["choice_id"] == choice_id), None)
    if not choice_data:
        return {"status": "error", "message": f"Выбор '{choice_id}' не найден"}

    ok, err = _check_conditions(run, choice_data.get("conditions"))
    if not ok:
        return {"status": "error", "message": err}

    snap_before = _snapshot_run(run)
    effects = choice_data.get("effects") or {}

    _apply_stats(run, dict(effects.get("stats") or {}))
    _apply_flags(run, effects.get("set_flags") or {})
    _apply_tags(run, effects.get("tags_add") or [])
    _apply_inventory(run, effects.get("items_add") or {},
                     effects.get("items_remove") or [])

    died = any(
        (b := next((x for x in snap_before["travelers"]
                    if x["name"] == t.name), None))
        and b["alive"] and not t.alive
        for t in run.travelers
    )
    if died and not effects.get("no_funeral"):
        if "need_funeral" not in run.tags:
            run.tags.append("need_funeral")

    consequences = _build_consequences(snap_before, run, choice_data)
    next_event_id = choice_data.get("next_event")
    run.current_event_id = next_event_id

    flag_modified(run, "inventory")
    flag_modified(run, "tags")
    db.session.commit()

    return {"status": "ok", "next_event": next_event_id,
            "run": run, "consequences": consequences}
