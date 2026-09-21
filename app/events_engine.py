"""
Движок вероятностей: «Режиссёр Драмы».

Решает, какой ивент случится сегодня (если случится вообще).
Не повторяет последние 5 событий.
"""

import random

from app.events_loader import get_daily_pool

# Шанс, что день пройдёт без событий. 5% — тихие дни редки.
QUIET_DAY_CHANCE = 0.05


def _check_triggers(run, triggers):
    """
    Проверяет, подходит ли текущее состояние Run под trigger_conditions.
    Возвращает True, если ивент МОЖЕТ случиться.
    """
    if not triggers:
        return True

    # --- День ---
    if "min_day" in triggers and run.day < triggers["min_day"]:
        return False
    if "max_day" in triggers and run.day > triggers["max_day"]:
        return False

    # --- Витамин C ---
    if "max_vit_c" in triggers and run.vit_c > triggers["max_vit_c"]:
        return False
    if "min_vit_c" in triggers and run.vit_c < triggers["min_vit_c"]:
        return False

    # --- Мораль ---
    if "max_morale" in triggers and run.morale > triggers["max_morale"]:
        return False
    if "min_morale" in triggers and run.morale < triggers["min_morale"]:
        return False

    # --- Отряд ---
    if "min_squad" in triggers and run.squad_size < triggers["min_squad"]:
        return False
    if "max_squad" in triggers and run.squad_size > triggers["max_squad"]:
        return False

    # --- Калории ---
    if "max_calories" in triggers and run.calories > triggers["max_calories"]:
        return False
    if "min_calories" in triggers and run.calories < triggers["min_calories"]:
        return False

    # --- Требуемый предмет ---
    if "required_item" in triggers:
        item = triggers["required_item"]
        if run.inventory.get(item, 0) <= 0:
            return False

    # --- Требуемый тег ---
    if "required_tag" in triggers:
        if triggers["required_tag"] not in run.tags:
            return False

    # --- Запрещённый тег ---
    if "forbidden_tag" in triggers:
        if triggers["forbidden_tag"] in run.tags:
            return False
    # Сезон: срабатывает только в указанных сезонах
    if "season_in" in triggers:
        if run.season not in triggers["season_in"]:
            return False

    return True


def _is_unique_already_seen(run, event_id, event_data):
    """Уникальный ивент нельзя выдать дважды."""
    if not event_data.get("is_unique"):
        return False
    return f"seen_{event_id}" in run.tags


def generate_daily_event(run):
    """
    Возвращает ID ивента на сегодня или None (тихий день).
    Не повторяет последние 5 событий.
    """
    daily_pool = get_daily_pool()
    recent = set(run.recent_events or [])

    available_events = []
    weights = []

    for event_id, event_data in daily_pool.items():
        # Не повторяем последние 5
        if event_id in recent:
            continue

        triggers = event_data.get("trigger_conditions") or {}
        if not _check_triggers(run, triggers):
            continue

        if _is_unique_already_seen(run, event_id, event_data):
            continue

        available_events.append(event_id)
        weights.append(event_data.get("weight", 10))

    if not available_events:
        return None

    if random.random() < QUIET_DAY_CHANCE:
        return None

    chosen_id = random.choices(available_events, weights=weights, k=1)[0]

    if daily_pool[chosen_id].get("is_unique"):
        tag = f"seen_{chosen_id}"
        if tag not in run.tags:
            run.tags.append(tag)

    # Обновляем recent_events
    recent_list = list(run.recent_events or [])
    recent_list.append(chosen_id)
    if len(recent_list) > 5:
        recent_list = recent_list[-5:]
    run.recent_events = recent_list

    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(run, "recent_events")

    return chosen_id


def get_available_events(run):
    """Для отладки: список ивентов, которые МОГУТ случиться сейчас."""
    daily_pool = get_daily_pool()
    recent = set(run.recent_events or [])
    result = []
    for event_id, event_data in daily_pool.items():
        if event_id in recent:
            continue
        triggers = event_data.get("trigger_conditions") or {}
        if _check_triggers(run, triggers) and not _is_unique_already_seen(
            run, event_id, event_data
        ):
            result.append(event_id)
    return result
