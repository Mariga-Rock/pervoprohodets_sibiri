"""
Загрузчик ивентов из data/events.json.

Кэширует JSON в памяти. Читает файл один раз при первом обращении.

Правило:
    Ни один маршрут не читает events.json напрямую.
    Все обращаются к этому модулю.
"""

import json
from pathlib import Path


# Путь: <корень_проекта>/data/events.json
# __file__ = app/events_loader.py
# .resolve().parent = app/
# .parent = корень проекта
_EVENTS_PATH = Path(__file__).resolve().parent.parent / "data" / "events.json"

_EVENTS_CACHE = None


def load_events():
    """
    Загружает events.json и кэширует результат.
    Повторные вызовы возвращают тот же словарь из памяти.
    """
    global _EVENTS_CACHE
    if _EVENTS_CACHE is None:
        if not _EVENTS_PATH.exists():
            raise FileNotFoundError(
                f"events.json не найден по пути: {_EVENTS_PATH}"
            )
        with open(_EVENTS_PATH, "r", encoding="utf-8") as f:
            _EVENTS_CACHE = json.load(f)
    return _EVENTS_CACHE


def reload_events():
    """
    Принудительно перечитывает events.json.
    Используется в dev-режиме, когда правишь JSON и не хочешь
    перезапускать Flask.
    """
    global _EVENTS_CACHE
    _EVENTS_CACHE = None
    return load_events()


def get_event(event_id: str):
    """Возвращает данные ивента по ID. None, если не найден."""
    return load_events().get(event_id)


def get_daily_pool():
    """
    Возвращает ивенты, доступные для дневной генерации.
    Исключает chain_only (они доступны только через next_event).
    """
    events = load_events()
    return {
        eid: edata
        for eid, edata in events.items()
        if not edata.get("chain_only", False)
    }


def get_events_count():
    """Для отладки и логов."""
    return len(load_events())
