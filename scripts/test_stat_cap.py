"""
Тест 6: ограничитель статов.

Калории = 280, выбор даёт +100.
Ожидается: calories = 300 (не 380), из-за MAX_CALORIES.
"""

import sys
from pathlib import Path
from sqlalchemy.orm.attributes import flag_modified

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from app.extensions import db
from app.models import User
from app.events_parser import process_event_choice
from app.constants import MAX_CALORIES

TG_ID = 123123123


def main():
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(telegram_id=TG_ID).first()
        if not user or not user.run:
            print(f"[FAIL] Игрок {TG_ID} не найден")
            sys.exit(1)

        run = user.run
        run.current_event_id = "event_frozen_elk"
        run.calories = 280      # близко к лимиту 300
        run.vit_c = 20
        run.morale = 80
        run.warmth = 100
        run.squad_size = 10
        run.inventory = {"salt": 2, "lancet": 1, "herbs": 3, "wood": 10}
        run.tags = []
        flag_modified(run, "inventory")
        flag_modified(run, "tags")
        db.session.commit()

        print(f"[OK] Игрок подготовлен:")
        print(f"     calories = {run.calories} (лимит {MAX_CALORIES})")

        # salt_meat даёт +100 калорий
        result = process_event_choice(run, "event_frozen_elk", "salt_meat")

        print(f"\n[<<<] status: {result['status']}")
        print(f"      calories после: {result['run'].calories}")

        if result["run"].calories != MAX_CALORIES:
            print(f"[FAIL] Ожидалось {MAX_CALORIES}, получено {result['run'].calories}")
            sys.exit(1)

        print(f"\n[PASS] Тест 6 пройден: лимит {MAX_CALORIES} сработал")


if __name__ == "__main__":
    main()
