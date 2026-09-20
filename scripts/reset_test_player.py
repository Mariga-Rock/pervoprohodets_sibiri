"""
Сбросить тестового игрока в начальное состояние ивента.

Использование:
    python scripts/reset_test_player.py
    python scripts/reset_test_player.py --event event_scurvy_start
    python scripts/reset_test_player.py --tg 555 --event none

По умолчанию: tg=123123123, event=event_frozen_elk, vit_c=20
"""

import argparse
import sys
from pathlib import Path
from sqlalchemy.orm.attributes import flag_modified

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from app.extensions import db
from app.models import User, Run


def reset(tg_id: int, event_id, vit_c: int):
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(telegram_id=tg_id).first()
        if not user or not user.run:
            print(f"[FAIL] Игрок {tg_id} не найден. "
                  f"Сначала запусти seed_test_player.py")
            return

        run = user.run
        run.day = 1
        run.distance_covered = 0
        run.calories = 100
        run.vit_c = vit_c
        run.morale = 80
        run.warmth = 100
        run.discipline=70
        run.squad_size = 10
        run.inventory = {"salt": 2, "lancet": 1, "herbs": 3, "wood": 10}
        run.tags = []
        run.current_event_id = event_id

        flag_modified(run, "inventory")
        flag_modified(run, "tags")

        db.session.commit()

        print(f"[OK] Игрок {tg_id} сброшен:")
        print(f"     current_event_id = {run.current_event_id}")
        print(f"     calories         = {run.calories}")
        print(f"     vit_c            = {run.vit_c}")
        print(f"     morale           = {run.morale}")
        print(f"     inventory        = {run.inventory}")
        print(f"     tags             = {run.tags}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tg", type=int, default=123123123)
    parser.add_argument("--event", type=str, default="event_frozen_elk")
    parser.add_argument("--vit-c", type=int, default=20)
    args = parser.parse_args()

    event_id = None if args.event == "none" else args.event
    reset(args.tg, event_id, args.vit_c)
