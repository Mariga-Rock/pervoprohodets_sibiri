"""
Flask-приложение. На этом этапе — только инициализация БД.
Маршруты добавим на Этапе 2.

Зачем нужен уже сейчас:
    Нужно создать таблицы в базе. Без app.py модели не с чем связать.
"""

import os
from dotenv import load_dotenv
from flask import Flask

# Загружаем .env ДО всего остального, чтобы os.environ видел переменные.
load_dotenv()

from extensions import db
from models import User, Run  # noqa: F401 — импорт нужен, чтобы SQLAlchemy увидела модели


def create_app():
    """Фабрика приложения. Стандартный паттерн Flask."""
    app = Flask(__name__)

    # ---- КОНФИГУРАЦИЯ ----
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-me')

    # DATABASE_URL из .env. По умолчанию — SQLite-файл app.db.
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL',
        'sqlite:///app.db'
    )

    # Отключаем трекинг изменений объектов (жрёт память, не нужен).
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # ---- ИНИЦИАЛИЗАЦИЯ ----
    db.init_app(app)

    return app


# Создаём приложение на уровне модуля.
# Это нужно, чтобы flask run подхватил его автоматически.
app = create_app()


if __name__ == '__main__':
    # Запуск через `python app.py` (для разработки).
    # Но рекомендую `flask run` — он правильнее работает с debug.
    app.run(debug=True)
