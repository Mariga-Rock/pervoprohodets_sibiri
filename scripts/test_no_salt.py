"""
Тест 4: попытка сделать выбор, требующий предмета, которого нет.

Шаги:
    1. Сбросить игрока в event_frozen_elk.
    2. Убрать соль из inventory.
    3. Отправить запрос make_choice с choice_id='salt_meat'.
    4. Проверить, что сервер вернул 400 и 'Не хватает предмета: salt'.
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
from app.models import User, Run

TG_ID = 123123123
BASE_URL = "http://127.0.0.1:5000"


def prepare_no_salt():
    """Сбрасывает игрока в event_frozen_elk без соли."""
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(telegram_id=TG_ID).first()
        if not user or not user.run:
            print(f"[FAIL] Игрок {TG_ID} не найден. Запусти seed_test_player.py")
            sys.exit(1)

        run = user.run
        run.current_event_id = "event_frozen_elk"
        run.calories = 100
        run.vit_c = 20
        run.morale = 80
        run.warmth = 100
        run.squad_size = 10
        run.inventory = {"lancet": 1, "herbs": 3, "wood": 10}  # соли нет
        run.tags = []
        flag_modified(run, "inventory")
        flag_modified(run, "tags")
        db.session.commit()

        print(f"[OK] Игрок подготовлен:")
        print(f"     current_event_id = {run.current_event_id}")
        print(f"     inventory        = {run.inventory}")
        return run.id


def post_json(url, payload):
    """Отправляет POST с JSON, возвращает (status_code, body_dict)."""
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
    prepare_no_salt()

    url = f"{BASE_URL}/api/make_choice"
    payload = {
        "telegram_id": TG_ID,
        "event_id": "event_frozen_elk",
        "choice_id": "salt_meat",
    }

    print(f"\n[>>>] POST {url}")
    print(f"      payload = {payload}\n")

    status, body = post_json(url, payload)

    print(f"[<<<] HTTP {status}")
    print(f"      body = {json.dumps(body, ensure_ascii=False, indent=2)}\n")

    # ---- ПРОВЕРКИ ----
    errors = []
    if status != 400:
        errors.append(f"Ожидался HTTP 400, получен {status}")
    if body.get("status") != "error":
        errors.append(f"Ожидался status='error', получен {body.get('status')!r}")
    if "salt" not in (body.get("message") or ""):
        errors.append(f"В сообщении нет 'salt': {body.get('message')!r}")

    if errors:
        print("[FAIL] Тест не пройден:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    print("[PASS] Тест 4 пройден: сервер отверг выбор без соли")


if __name__ == "__main__":
    main()
