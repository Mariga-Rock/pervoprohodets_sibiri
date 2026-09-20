"""
Тест /api/next_turn через HTTP.

Прогоняем 30 дней подряд и смотрим, как меняется состояние.
"""

import sys
import json
import urllib.request
import urllib.error
from pathlib import Path
from sqlalchemy.orm.attributes import flag_modified

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from app.extensions import db
from app.models import User

TG_ID = 123123123
BASE_URL = "http://127.0.0.1:5000"


def prepare():
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(telegram_id=TG_ID).first()
        if not user or not user.run:
            print(f"[FAIL] Игрок {TG_ID} не найден")
            sys.exit(1)
        run = user.run
        run.current_event_id = None
        run.day = 1
        run.distance_covered = 0
        run.calories = 300
        run.vit_c = 100
        run.morale = 100
        run.warmth = 100
        run.squad_size = 10
        run.inventory = {"salt": 2, "lancet": 1, "herbs": 3, "wood": 10}
        run.tags = []
        flag_modified(run, "tags")
        db.session.commit()
        print("[OK] Игрок подготовлен к прогону")


def post_json(url, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def main():
    prepare()

    url = f"{BASE_URL}/api/next_turn"
    quiet_days = 0
    event_days = 0

    for i in range(30):
        status, body = post_json(url, {"telegram_id": TG_ID})

        if status != 200:
            print(f"[FAIL] HTTP {status}: {body}")
            sys.exit(1)

        if body.get("status") == "game_over":
            print(f"\n[GAME OVER] день {body.get('day')}: {body.get('reason')}")
            break

        if body.get("type") == "event":
            event_days += 1
            print(f"[День {body['run']['day']:2d}] "
                  f"ИВЕНТ: {body['event_id']} — {body['event_title']}")
            # Нужно сделать выбор, чтобы продолжить
            print(f"          доступные выборы: "
                  f"{[c['choice_id'] for c in body['choices']]}")
            break  # встали в ивент — выходим из цикла

        else:  # quiet_day
            quiet_days += 1
            run = body["run"]
            print(f"[День {run['day']:2d}] тихий день | "
                  f"cal={run['calories']:3d} vit_c={run['vit_c']:3d} "
                  f"morale={run['morale']:3d}")

    print(f"\nИтого за прогон:")
    print(f"  тихих дней: {quiet_days}")
    print(f"  ивентов:    {event_days}")


if __name__ == "__main__":
    main()
