"""
Проверка полной цепочки:
    смерть казака → тег need_funeral → next_turn → event_funeral обязательно.
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
from app.events_parser import process_event_choice

TG_ID = 123123123
BASE_URL = "http://127.0.0.1:5000"


def post_json(url, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def main():
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(telegram_id=TG_ID).first()
        if not user or not user.run:
            print("[FAIL] Игрок не найден")
            sys.exit(1)

        run = user.run
        run.current_event_id = "event_gangrene_battle"
        run.calories = 100
        run.vit_c = 20
        run.morale = 80
        run.warmth = 100
        run.discipline = 70
        run.squad_size = 10
        run.has_priest = True
        run.inventory = {"salt": 2, "lancet": 1, "herbs": 3, "wood": 10}
        run.tags = []
        flag_modified(run, "inventory")
        flag_modified(run, "tags")
        db.session.commit()

        squad_before = run.squad_size

        # Выбор "wait" — казак умирает
        result = process_event_choice(
            run, "event_gangrene_battle", "wait"
        )
        squad_after = result["run"].squad_size
        tags = result["run"].tags

        print(f"Отряд: {squad_before} → {squad_after}")
        print(f"Теги: {tags}")

        if "need_funeral" not in tags:
            print("[FAIL] need_funeral не добавлен")
            sys.exit(1)

    # Теперь вызываем next_turn через HTTP
    status, body = post_json(
        f"{BASE_URL}/api/next_turn", {"telegram_id": TG_ID}
    )
    print(f"\nnext_turn → HTTP {status}")
    print(f"  type: {body.get('type')}")
    print(f"  event_id: {body.get('event_id')}")

    if body.get("event_id") != "event_funeral":
        print("[FAIL] Молебен не сработал!")
        sys.exit(1)

    print("\n[PASS] Молебен сработал обязательно")


if __name__ == "__main__":
    main()
