"""
Парсер ивентов. Мост между JSON-сценарием и БД.

Принимает выбор игрока, проверяет его, применяет эффекты,
сохраняет в БД, возвращает результат.

Три уровня защиты:
    1. Рассинхронизация — run.current_event_id должен совпадать с event_id.
    2. Валидация предметов — если для выбора нужен предмет, он должен быть.
    3. Ограничители статов — статы не уходят в минус и не превышают максимум.
"""

from sqlalchemy.orm.attributes import flag_modified

from app.extensions import db
from app.events_loader import get_event
from app.constants import (
    MAX_CALORIES, MAX_VIT_C, MAX_MORALE, MAX_WARMTH,
)


# ---------------------------------------------------------------------------
# СЛЕПКИ И ПОСЛЕДСТВИЯ
# ---------------------------------------------------------------------------
def _snapshot_run(run):
    """Слепок состояния Run ДО применения эффектов."""
    return {
        "calories": run.calories,
        "vit_c": run.vit_c,
        "morale": run.morale,
        "warmth": run.warmth,
        "discipline": run.discipline,
        "squad_size": run.squad_size,
        "inventory": dict(run.inventory),
    }


def _build_consequences(snap_before, run, choice_data):
    """
    Собирает последствия: нарратив (из JSON, если есть) + список дельт.
    Дельта пишется только для того, что реально изменилось.
    """
    deltas = []

    checks = [
        ("calories",   "к калориям"),
        ("vit_c",      "к витамину C"),
        ("morale",     "к морали"),
        ("warmth",     "к теплу"),
        ("discipline", "к дисциплине"),
        ("squad_size", "к отряду"),
    ]
    for field, label in checks:
        before = snap_before[field]
        after = getattr(run, field)
        if before != after:
            d = after - before
            sign = "+" if d > 0 else "−"
            deltas.append(f"{sign}{abs(d)} {label}")

    # Инвентарь — что добавилось / убавилось
    items = set(snap_before["inventory"].keys()) | set(run.inventory.keys())
    for item in sorted(items):
        before = snap_before["inventory"].get(item, 0)
        after = run.inventory.get(item, 0)
        if before != after:
            d = after - before
            sign = "+" if d > 0 else "−"
            deltas.append(f"{sign}{abs(d)} {item}")

    narrative = choice_data.get("consequences")
    if not narrative:
        narrative = f"Вы выбрали: {choice_data.get('text', '')}."

    return {
        "narrative": narrative,
        "deltas": deltas,
    }


# ---------------------------------------------------------------------------
# ПРИМЕНЕНИЕ ЭФФЕКТОВ
# ---------------------------------------------------------------------------
def _apply_stats(run, stats_diff):
    """Применяет изменения статов с ограничителями."""
    if not stats_diff:
        return

    if "calories" in stats_diff:
        run.calories = max(0, min(run.calories + stats_diff["calories"], MAX_CALORIES))
    if "vit_c" in stats_diff:
        run.vit_c = max(0, min(run.vit_c + stats_diff["vit_c"], MAX_VIT_C))
    if "morale" in stats_diff:
        run.morale = max(0, min(run.morale + stats_diff["morale"], MAX_MORALE))
    if "warmth" in stats_diff:
        run.warmth = max(0, min(run.warmth + stats_diff["warmth"], MAX_WARMTH))
    if "discipline" in stats_diff:
        run.discipline = max(0, min(run.discipline + stats_diff["discipline"], 100))
    if "squad_size" in stats_diff:
        run.squad_size = max(0, run.squad_size + stats_diff["squad_size"])


def _apply_tags(run, tags_to_add):
    """Добавляет теги. Не допускает дубликатов."""
    if not tags_to_add:
        return
    for tag in tags_to_add:
        if tag not in run.tags:
            run.tags.append(tag)


def _apply_inventory(run, items_add, items_remove):
    """Добавляет/убирает предметы. Если количество уходит в 0 — удаляет ключ."""
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
    """
    Проверяет, выполнены ли условия выбора.
    Возвращает (True, None) или (False, "причина").
    """
    if not conditions:
        return True, None

    required = conditions.get("items_required") or {}
    for item, qty in required.items():
        if run.inventory.get(item, 0) < qty:
            return False, f"Не хватает предмета: {item}"

    required_tags = conditions.get("tags_required") or []
    for tag in required_tags:
        if tag not in run.tags:
            return False, f"Не хватает условия: {tag}"

    stats_min = conditions.get("stats_min") or {}
    for stat, min_val in stats_min.items():
        if getattr(run, stat, 0) < min_val:
            return False, f"Слишком низкий {stat}"

    stats_max = conditions.get("stats_max") or {}
    for stat, max_val in stats_max.items():
        if getattr(run, stat, 0) > max_val:
            return False, f"Слишком высокий {stat}"

    return True, None


# ---------------------------------------------------------------------------
# ГЛАВНАЯ ФУНКЦИЯ
# ---------------------------------------------------------------------------
def process_event_choice(run, event_id: str, choice_id: str):
    """
    Обрабатывает выбор игрока.
    Возвращает:
        Успех:  {"status": "ok", "next_event": <id|None>, "run": <Run>,
                 "consequences": {...}}
        Ошибка: {"status": "error", "message": "..."}
    """
    # 1. РАССИНХРОНИЗАЦИЯ
    if run.current_event_id != event_id:
        return {
            "status": "error",
            "message": (
                f"Рассинхронизация: ожидался ивент "
                f"'{run.current_event_id}', получен '{event_id}'"
            ),
        }

    # 2. ИВЕНТ СУЩЕСТВУЕТ?
    event_data = get_event(event_id)
    if not event_data:
        return {
            "status": "error",
            "message": f"Ивент '{event_id}' не найден",
        }

    # 3. ВЫБОР СУЩЕСТВУЕТ?
    choice_data = None
    for ch in event_data["choices"]:
        if ch["choice_id"] == choice_id:
            choice_data = ch
            break

    if not choice_data:
        return {
            "status": "error",
            "message": (
                f"Выбор '{choice_id}' не найден в ивенте '{event_id}'"
            ),
        }

    # 4. УСЛОВИЯ ВЫБОРА
    ok, err = _check_conditions(run, choice_data.get("conditions"))
    if not ok:
        return {"status": "error", "message": err}

    # 5. СНИМОК ДО ЭФФЕКТОВ
    snap_before = _snapshot_run(run)

    # 6. ПРИМЕНЕНИЕ ЭФФЕКТОВ
    effects = choice_data.get("effects") or {}
    _apply_stats(run, effects.get("stats") or {})
    _apply_tags(run, effects.get("tags_add") or [])
    _apply_inventory(
        run,
        effects.get("items_add") or {},
        effects.get("items_remove") or [],
    )

    # 7. СМЕРТЬ КАЗАКА → ТРЕБУЕТСЯ МОЛЕБЕН
    if run.squad_size < snap_before["squad_size"]:
        if "need_funeral" not in run.tags:
            run.tags.append("need_funeral")

    # 8. ПОСЛЕДСТВИЯ
    consequences = _build_consequences(snap_before, run, choice_data)

    # 9. NEXT EVENT
    next_event_id = choice_data.get("next_event")
    run.current_event_id = next_event_id

    # 10. МАГИЯ SQLALCHEMY ДЛЯ JSON-ПОЛЕЙ
    flag_modified(run, "inventory")
    flag_modified(run, "tags")

    # 11. СОХРАНЕНИЕ
    db.session.commit()

    return {
        "status": "ok",
        "next_event": next_event_id,
        "run": run,
        "consequences": consequences,
    }
