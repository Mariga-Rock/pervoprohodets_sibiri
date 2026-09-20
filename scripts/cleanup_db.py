"""
Удаляет всех User и все Run из БД.

ВНИМАНИЕ: только для локальной разработки!
В продакшене — НИКОГДА не запускать.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from app.extensions import db
from app.models import User, Run


def cleanup():
    app = create_app()
    with app.app_context():
        user_count = User.query.count()
        run_count = Run.query.count()

        print(f"До очистки: User={user_count}, Run={run_count}")

        # Сначала Run — на случай сирот без User
        Run.query.delete()
        User.query.delete()
        db.session.commit()

        print(f"После очистки: User={User.query.count()}, "
              f"Run={Run.query.count()}")


if __name__ == "__main__":
    confirm = input("Удалить ВСЕ данные? Введи 'yes' для подтверждения: ")
    if confirm.strip().lower() != "yes":
        print("Отменено.")
        sys.exit(0)
    cleanup()
