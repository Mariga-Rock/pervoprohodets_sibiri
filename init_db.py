"""
Скрипт создания таблиц в БД.

Запуск:
    python init_db.py

Что делает:
    Создаёт все таблицы, описанные в models.py.
    Если таблицы уже существуют — ничего не трогает.

Когда запускать:
    Один раз после создания моделей.
    Ещё раз — если добавил новую модель (например, Message для «Завещания во льдах»).
    НЕ запускать, если менял поля существующих таблиц — тогда нужна миграция.
"""

from app import app, db

# Импорт моделей — обязателен. Без него SQLAlchemy не знает, что создавать.
from models import User, Run  # noqa: F401


def init_database():
    with app.app_context():
        db.create_all()
        print("[OK] Таблицы созданы (или уже существовали):")
        print(f"     - users")
        print(f"     - runs")
        print(f"\nБаза данных: {app.config['SQLALCHEMY_DATABASE_URI']}")


if __name__ == '__main__':
    init_database()
