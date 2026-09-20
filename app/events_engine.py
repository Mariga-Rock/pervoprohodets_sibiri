"""
Движок вероятностей: «Режиссёр Драмы».

Решает, какой ивент случится сегодня (если случится вообще).
Работает в три этапа:
    1. Фильтрация — отбрасываем нелогичные ивенты.
    2. Взвешивание — собираем веса оставшихся.
    3. Бросок кубика — выбираем по весам или возвращаем None (тихий день).

Ключевая идея:
    Если у игрока всё хорошо (vit_c = 100, morale = 100), движок физически
    не может выдать ивенты про цингу или бунт — их отфильтруют
    trigger_conditions. Как только статы падают — пул расширяется.
"""

import random

from app.events_loader import get_daily_pool

# Шанс, что день пройдёт без событий. 20% — это «воздух» между ивентами.
QUIET_DAY_CHANCE = 0.05


def _check_triggers(run, triggers):
    """
    Проверяет, подходит ли текущее состояние Run под trigger_conditions.

    Возвращает True, если ивент МОЖЕТ случиться, False — если нет.
    """
    if not triggers:
        return True

    # --- День ---
    if "min_day" in triggers and run.day < triggers["min_day"]:
        return False
    if "max_day" in triggers and run.day > triggers["max_day"]:
        return False

    # --- Витамин C: ивент цинги не может случиться при высоком vit_c ---
    if "max_vit_c" in triggers and run.vit_c > triggers["max_vit_c"]:
        return False
    if "min_vit_c" in triggers and run.vit_c < triggers["min_vit_c"]:
        return False

    # --- Мораль: ивент бунта не может случиться при высокой морали ---
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

    return True


def _is_unique_already_seen(run, event_id, event_data):
    """Уникальный ивент нельзя выдать дважды. Проверяем по тегу."""
    if not event_data.get("is_unique"):
        return False
    return f"seen_{event_id}" in run.tags


def generate_daily_event(run):
    """
    Возвращает ID ивента, который случится сегодня, или None (тихий день).

    Шаги:
        1. Берём дневной пул (без chain_only).
        2. Отбрасываем те, что не проходят trigger_conditions.
        3. Отбрасываем уникальные, которые уже видели.
        4. Бросок кубика: 20% шанс тихого дня.
        5. Взвешенный выбор.
        6. Если ивент уникальный — вешаем тег seen_<id>.

    НЕ коммитит в БД. Коммит делает вызывающий код.
    """
    daily_pool = get_daily_pool()

    available_events = []
    weights = []

    for event_id, event_data in daily_pool.items():
        # 1. Триггеры
        triggers = event_data.get("trigger_conditions") or {}
        if not _check_triggers(run, triggers):
            continue

        # 2. Уникальность
        if _is_unique_already_seen(run, event_id, event_data):
            continue

        available_events.append(event_id)
        weights.append(event_data.get("weight", 10))

    # 3. Ничего не доступно — тихий день
    if not available_events:
        return None

    # 4. 20% шанс тихого дня — даже если пул не пустой
    if random.random() < QUIET_DAY_CHANCE:
        return None

    # 5. Взвешенный выбор
    chosen_id = random.choices(
        available_events, weights=weights, k=1
    )[0]

    # 6. Уникальный ивент — вешаем тег, чтобы не выпал снова
    if daily_pool[chosen_id].get("is_unique"):
        tag = f"seen_{chosen_id}"
        if tag not in run.tags:
            run.tags.append(tag)

    return chosen_id


def get_available_events(run):
    """
    Для отладки: возвращает список ID ивентов, которые МОГУТ случиться
    в текущем состоянии Run (без учёта 20% тихого дня).
    """
    daily_pool = get_daily_pool()
    result = []
    for event_id, event_data in daily_pool.items():
        triggers = event_data.get("trigger_conditions") or {}
        if _check_triggers(run, triggers) and not _is_unique_already_seen(
            run, event_id, event_data
        ):
            result.append(event_id)
    return result
