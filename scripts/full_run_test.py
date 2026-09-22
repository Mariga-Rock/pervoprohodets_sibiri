"""
Автоматический прогон 100 вёрст через HTTP.

Что делает:
    1. Создаёт тестового игрока.
    2. Каждый ход — next_turn.
    3. Если выпал ивент — делает первый доступный выбор
       (приоритет: безопасные действия без боя).
    4. Логирует: день, год, сезон, дистанцию, событие, статы.
    5. Останавливается на победе или смерти.

Запуск (Flask должен работать):
    python scripts/full_run_test.py
    python scripts/full_run_test.py --tg 555
    python scripts/full_run_test.py --max-turns 200
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BASE_URL = "http://127.0.0.1:5000"


# Предпочтения выбора (первый доступный из списка)
SAFE_CHOICES = [
    # Мир и дипломатия
    "listen", "observe", "pray", "wait", "wait_it_out",
    "record", "ask_more", "continue", "accept", "quick",
    # Медицина
    "pine_brew", "cheremsha", "berries", "warm_water",
    "operate", "amputate",
    # Еда
    "kill_horses", "raid_camp", "salt_meat", "thaw_it",
    "full_day", "half_day",
    # Сюжет
    "garrison", "hold", "night_assault", "flank",
    "swear", "oath", "trade", "trade_fur", "gift",
    # Защита
    "fire", "fire_warning", "big_fire",
    # Спасение
    "set_watch", "warn_ermak",
    "let_die", "throw_liver", "refuse_eat",
    # Конец
    "cross", "winter_camp", "write_letter",
]


def post_json(path, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        BASE_URL + path, data=data, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, {"error": "unreadable"}


def pick_choice(choices):
    """Выбирает первый доступный выбор из списка предпочтений."""
    ids = [c["choice_id"] for c in choices]
    for safe in SAFE_CHOICES:
        if safe in ids:
            return safe
    # Иначе — первый попавшийся
    return ids[0] if ids else None


def main(tg_id, max_turns):
    print(f"=== Прогон для tg_id={tg_id} ===")

    # 1. Сброс игрока
    status, body = post_json("/api/start_game", {"telegram_id": tg_id,
                                                  "username": "autotest"})
    if status != 200 or body.get("status") not in ("created",
                                                     "already_running"):
        print(f"[FAIL] start_game: {status} {body}")
        return

    run = body.get("run", {})
    print(f"Старт: день {run.get('day')}, год {run.get('year')}, "
          f"{run.get('season_name')}, дистанция {run.get('distance_covered')}")

    # 2. Цикл
    for turn in range(max_turns):
        # Если игрок в ивенте — делаем выбор
        state_status, state = post_json("/api/get_state",
                                         {"telegram_id": tg_id})
        if state_status != 200:
            print(f"[FAIL] get_state: {state_status}")
            return

        run = state.get("run", {})
        current_event = run.get("current_event_id")

        if current_event:
            # Запрашиваем ивент
            ev_status, ev = post_json("/api/get_event",
                                       {"telegram_id": tg_id,
                                        "event_id": current_event})
            if ev_status != 200 or ev.get("status") != "ok":
                print(f"[FAIL] get_event {current_event}: "
                      f"{ev_status} {ev}")
                return

            choices = ev.get("choices", [])
            if not choices:
                # Ивент без выборов — пропускаем
                print(f"  ! ивент {current_event} без выборов")
                continue

            choice_id = pick_choice(choices)
            if not choice_id:
                print(f"  ! нет доступного выбора в {current_event}")
                return

            ch_status, ch_body = post_json("/api/make_choice",
                                            {"telegram_id": tg_id,
                                             "event_id": current_event,
                                             "choice_id": choice_id})
            if ch_status != 200:
                print(f"[FAIL] make_choice {current_event}.{choice_id}: "
                      f"{ch_status} {ch_body}")
                return

            # Если chain — продолжаем без хода
            next_ev = ch_body.get("next_event")
            if next_ev:
                print(f"  Д{run.get('day')} [{run.get('season_name')}] "
                      f"ДИСТ {run.get('distance_covered')} | "
                      f"{current_event}.{choice_id} → {next_ev}")
                continue
            else:
                print(f"  Д{run.get('day')} [{run.get('season_name')}] "
                      f"ДИСТ {run.get('distance_covered')} | "
                      f"{current_event}.{choice_id}")
                continue

        # Иначе — ход
        turn_status, turn_body = post_json("/api/next_turn",
                                            {"telegram_id": tg_id})
        if turn_status != 200:
            print(f"[FAIL] next_turn: {turn_status} {turn_body}")
            return

        # Game over
        if turn_body.get("status") == "game_over":
            print(f"\n☠ GAME OVER на дне {turn_body.get('day')}: "
                  f"{turn_body.get('reason')}")
            print(f"Дистанция: {turn_body.get('distance_covered')}")
            return

        # Victory
        if turn_body.get("status") == "victory":
            print(f"\n✦ VICTORY на дне {turn_body.get('day')}!")
            print(f"Дистанция: {turn_body.get('distance_covered')}")
            break

        # Обычный ход
        run = turn_body.get("run", {})
        event_id = turn_body.get("event_id") or turn_body.get("type", "?")
        print(f"  Д{run.get('day'):3d} [{run.get('season_name'):5s}] "
              f"Г{run.get('year')} ДИСТ {run.get('distance_covered'):3d} | "
              f"{event_id}")

        # Раз в 20 ходов — статы
        if turn % 20 == 0:
            print(f"      статы: мука={run.get('flour')} "
                  f"рыба={run.get('fish')} мясо={run.get('meat')} "
                  f"vit={run.get('vit_c')} мор={run.get('morale')} "
                  f"отр={run.get('squad_size')}/{run.get('wounded')}")

        time.sleep(0.05)

    else:
        print(f"\n[WARN] Прогон завершён за {max_turns} ходов, "
              f"но победы нет")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tg", type=int, default=123123123)
    parser.add_argument("--max-turns", type=int, default=300)
    args = parser.parse_args()
    main(args.tg, args.max_turns)
