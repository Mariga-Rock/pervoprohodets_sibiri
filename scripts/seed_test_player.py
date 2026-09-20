"""
Создать или сбросить тестового игрока для проверки ивентов.

Запуск:
    python scripts/seed_test_player.py

По умолчанию создаёт:
    telegram_id = 123123123
    vit_c       = 20   (ниже порога цинги — можно тестировать цингу)
    current_event_id = "event_frozen_elk"

Можно менять параметры через аргументы командной строки:
    python scripts/seed_test_player.py --tg 555 --event event_scurvy_start
"""

import argparse
import sys
from pathlib import Path

# Добавляем корень проекта в sys.path, чтобы импорты работали
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm.attributes import flag_modified

from app import create_app
from app.extensions import db
from app.models import User, Run


def seed(tg_id: int, event_id: str | None, vit_c: int):
    app = create_app()
    with app.app_context():
        # 1. Удаляем старого тестового, если был
        old = User.query.filter_by(telegram_id=tg_id).first()
        if old:
            db.session.delete(old)
            db.session.commit()

        # 2. Создаём User
        user = User(telegram_id=tg_id, username="tester")
        db.session.add(user)
        db.session.flush()  # получаем user.id

        # 3. Создаём Run
        run = Run(
            user_id=user.id,
            day=1,
            distance_covered=0,
            calories=100,
            vit_c=vit_c,
            morale=80,
            warmth=100,
            squad_size=10,
            inventory={"salt": 2, "lancet": 1, "herbs": 3, "wood": 10},
            tags=[],
            current_event_id=event_id,
        )
        db.session.add(run)
        db.session.commit()

        print(f"[OK] Тестовый игрок создан")
        print(f"     telegram_id      = {user.telegram_id}")
        print(f"     run.id           = {run.id}")
        print(f"     calories         = {run.calories}")
        print(f"     vit_c            = {run.vit_c}")
        print(f"     morale           = {run.morale}")
        print(f"     inventory        = {run.inventory}")
        print(f"     current_event_id = {run.current_event_id}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tg", type=int, default=123123123,
                        help="telegram_id тестового игрока")
    parser.add_argument("--event", type=str, default="event_frozen_elk",
                        help="ID ивента, в который поставить игрока "
                             "(или 'none' чтобы не ставить)")
    parser.add_argument("--vit-c", type=int, default=20,
                        help="стартовое значение витамина C")
    args = parser.parse_args()

    event_id = None if args.event == "none" else args.event
    seed(args.tg, event_id, args.vit_c)
