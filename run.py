"""
Точка входа для запуска Flask-приложения.

Запуск:
    python run.py

Почему отдельный файл:
    Сам пакет app/ не умеет запускаться сам по себе (нет __main__).
    Нужен внешний скрипт, который создаст app и запустит его.
"""

from app import create_app

app = create_app()


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
if __name__ == '__main__':
    print("=== DB URI:", app.config['SQLALCHEMY_DATABASE_URI'], "===")
    app.run(debug=True)
