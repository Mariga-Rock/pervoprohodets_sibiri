"""
Проверка валидности data/events.json.

Проверяет:
    - обязательные поля верхнего уровня (text, choices);
    - уникальность choice_id внутри ивента;
    - что next_event ссылается на существующий ивент;
    - что effects.stats содержит только известные статы.

Запуск:
    python scripts/validate_events.py
"""

import json
import sys
from pathlib import Path

# Путь: <корень>/data/events.json
EVENTS_PATH = Path(__file__).resolve().parent.parent / "data" / "events.json"

# Какие статы мы умеем обрабатывать.
# Если JSON содержит что-то другое — ошибка.
VALID_STAT_KEYS = {"calories", "vit_c", "morale", "discipline", "squad_size"}


def validate():
    if not EVENTS_PATH.exists():
        print(f"[FAIL] Файл не найден: {EVENTS_PATH}")
        sys.exit(1)

    with open(EVENTS_PATH, "r", encoding="utf-8") as f:
        events = json.load(f)

    all_ids = set(events.keys())
    errors = []

    for eid, ev in events.items():
        # --- ВЕРХНИЙ УРОВЕНЬ ---
        if "text" not in ev:
            errors.append(f"{eid}: нет поля 'text'")
        if "choices" not in ev or not isinstance(ev["choices"], list):
            errors.append(f"{eid}: нет 'choices' или это не список")
            continue
        if not ev["choices"]:
            errors.append(f"{eid}: 'choices' пустой")

        # --- ВЫБОРЫ ---
        choice_ids = set()
        for i, ch in enumerate(ev["choices"]):
            # Обязательные поля
            for field in ("choice_id", "text"):
                if field not in ch:
                    errors.append(f"{eid}.choices[{i}]: нет '{field}'")

            cid = ch.get("choice_id", f"<{i}>")

            # Уникальность
            if cid in choice_ids:
                errors.append(f"{eid}: дубликат choice_id '{cid}'")
            choice_ids.add(cid)

            # next_event — должен существовать
            nxt = ch.get("next_event")
            if nxt is not None and nxt not in all_ids:
                errors.append(
                    f"{eid}.{cid}: next_event '{nxt}' не существует"
                )

            # effects.stats — только известные ключи
            stats = (ch.get("effects") or {}).get("stats") or {}
            if not isinstance(stats, dict):
                errors.append(f"{eid}.{cid}: effects.stats не словарь")
                continue
            for k in stats.keys():
                if k not in VALID_STAT_KEYS:
                    errors.append(
                        f"{eid}.{cid}: неизвестный стат '{k}'. "
                        f"Допустимо: {sorted(VALID_STAT_KEYS)}"
                    )

        # --- CHAIN_ONLY не должен иметь trigger_conditions ---
        if ev.get("chain_only") and "trigger_conditions" in ev:
            errors.append(
                f"{eid}: chain_only не должен иметь trigger_conditions"
            )

    if errors:
        print("[FAIL] Ошибки в events.json:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    # --- УСПЕХ ---
    print(f"[OK] events.json валиден. Всего ивентов: {len(events)}")
    for eid, ev in events.items():
        flags = []
        if ev.get("is_unique"):
            flags.append("unique")
        if ev.get("chain_only"):
            flags.append("chain_only")
        tag = f" [{' / '.join(flags)}]" if flags else ""
        print(f"  - {eid}: {ev.get('title', '?')}{tag}")


if __name__ == "__main__":
    validate()
