"""
Тест 5: цепочка ивентов.

eat_raw в event_frozen_elk → event_frozen_elk_disgust
continue в chain-ивенте → выход в null
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


def prepare():
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(telegram_id=TG_ID).first()
        if not user or not user.run:
            print(f"[FAIL] Игрок {TG_ID} не найден")
            sys.exit(1)
        run = user.run
        run.current_event_id = "event_frozen_elk"
        run.calories = 100
        run.vit_c = 20
        run.morale = 80
        run.warmth = 100
        run.squad_size = 10
        run.inventory = {"salt": 2, "lancet": 1, "herbs": 3, "wood": 10}
        run.tags = []
        flag_modified(run, "inventory")
        flag_modified(run, "tags")
        db.session.commit()
        return run.id


def call(event_id, choice_id):
    """Вызывает process_event_choice напрямую, минуя HTTP."""
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(telegram_id=TG_ID).first()
        result = process_event_choice(user.run, event_id, choice_id)
        return result


def main():
    prepare()

    # Шаг 1
    print("[Шаг 1] eat_raw в event_frozen_elk")
    r1 = call("event_frozen_elk", "eat_raw")
    print(f"  status:      {r1['status']}")
    print(f"  next_event:  {r1['next_event']}")
    print(f"  calories:    {r1['run'].calories}")
    print(f"  tags:        {r1['run'].tags}")

    if r1["next_event"] != "event_frozen_elk_disgust":
        print("[FAIL] Ожидался next_event='event_frozen_elk_disgust'")
        sys.exit(1)

    # Шаг 2
    print("\n[Шаг 2] continue в event_frozen_elk_disgust")
    r2 = call("event_frozen_elk_disgust", "continue")
    print(f"  status:      {r2['status']}")
    print(f"  next_event:  {r2['next_event']}")
    print(f"  current_event_id: {r2['run'].current_event_id}")

    if r2["next_event"] is not None:
        print("[FAIL] Ожидался next_event=None")
        sys.exit(1)
    if r2["run"].current_event_id is not None:
        print("[FAIL] Ожидался current_event_id=None")
        sys.exit(1)

    print("\n[PASS] Тест 5 пройден: цепочка работает")


if __name__ == "__main__":
    main()
