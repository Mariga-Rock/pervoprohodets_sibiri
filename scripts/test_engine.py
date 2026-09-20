"""
Тест движка вероятностей.

Проверяет, что generate_daily_event():
    - при высоком vit_c НЕ выдаёт цингу;
    - при низком vit_c и day >= 5 ВЫДАЁТ цингу (если пул не пуст);
    - chain_only ивент НИКОГДА не выдаётся как дневной;
    - is_unique ивент выдаётся только один раз.

Запуск:
    python scripts/test_engine.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from app.extensions import db
from app.models import User
from app.events_engine import get_available_events, generate_daily_event
from app.events_loader import get_event

TG_ID = 123123123


def _reset_run(run, **overrides):
    """Сбрасывает Run в базовое состояние + overrides."""
    run.current_event_id = None
    run.day = 1
    run.distance_covered = 0
    run.calories = 300
    run.vit_c = 100
    run.morale = 100
    run.warmth = 100
    run.squad_size = 10
    run.inventory = {"salt": 2, "lancet": 1, "herbs": 3, "wood": 10}
    run.tags = []
    for k, v in overrides.items():
        setattr(run, k, v)


def test_high_vit_c():
    """При vit_c=100 цинга не должна попасть в пул."""
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(telegram_id=TG_ID).first()
        run = user.run
        _reset_run(run, day=10, vit_c=100)
        db.session.commit()

        pool = get_available_events(run)
        print(f"  vit_c=100, day=10 → пул: {pool}")

        if "event_scurvy_start" in pool:
            print("  [FAIL] Цинга в пуле при высоком vit_c!")
            return False
        print("  [OK] Цинги нет в пуле")
        return True


def test_low_vit_c():
    """При vit_c=20 и day >= 5 цинга ДОЛЖНА попасть в пул."""
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(telegram_id=TG_ID).first()
        run = user.run
        _reset_run(run, day=10, vit_c=20)
        db.session.commit()

        pool = get_available_events(run)
        print(f"  vit_c=20, day=10 → пул: {pool}")

        if "event_scurvy_start" not in pool:
            print("  [FAIL] Цинги нет в пуле при низком vit_c!")
            return False
        print("  [OK] Цинга в пуле")
        return True


def test_low_vit_c_early_day():
    """При vit_c=20, но day < 5 цинга НЕ должна попасть (min_day: 5)."""
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(telegram_id=TG_ID).first()
        run = user.run
        _reset_run(run, day=3, vit_c=20)
        db.session.commit()

        pool = get_available_events(run)
        print(f"  vit_c=20, day=3 → пул: {pool}")

        if "event_scurvy_start" in pool:
            print("  [FAIL] Цинга в пуле до min_day!")
            return False
        print("  [OK] Цинги нет в пуле (day < min_day)")
        return True


def test_chain_only_never_daily():
    """chain_only ивент не должен попадать в пул."""
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(telegram_id=TG_ID).first()
        run = user.run
        _reset_run(run, day=20, vit_c=10)
        db.session.commit()

        pool = get_available_events(run)
        print(f"  пул: {pool}")

        if "event_frozen_elk_disgust" in pool:
            print("  [FAIL] chain_only в дневном пуле!")
            return False
        print("  [OK] chain_only не в пуле")
        return True


def test_unique_only_once():
    """Уникальный ивент выдаётся только один раз."""
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(telegram_id=TG_ID).first()
        run = user.run
        _reset_run(run, day=10, vit_c=20)
        db.session.commit()

        # Первый раз цинга должна быть в пуле
        pool1 = get_available_events(run)
        if "event_scurvy_start" not in pool1:
            print("  [FAIL] Цинги нет в пуле до тега!")
            return False
        print(f"  до тега: пул содержит цингу")

        # Вешаем тег, как будто уже видели
        run.tags.append("seen_event_scurvy_start")
        db.session.commit()

        pool2 = get_available_events(run)
        print(f"  после тега: пул = {pool2}")

        if "event_scurvy_start" in pool2:
            print("  [FAIL] Цинга осталась в пуле после тега!")
            return False
        print("  [OK] Цинга исчезла из пула")
        return True


def test_generate_stable():
    """generate_daily_event возвращает либо None, либо валидный ID."""
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(telegram_id=TG_ID).first()
        run = user.run
        _reset_run(run, day=10, vit_c=20)
        db.session.commit()

        results = {}
        for _ in range(200):
            event_id = generate_daily_event(run)
            results[event_id] = results.get(event_id, 0) + 1

        print(f"  200 запусков → {results}")

        # Все не-None должны быть валидными ивентами из пула
        for eid in results:
            if eid is None:
                continue
            if get_event(eid) is None:
                print(f"  [FAIL] Неизвестный ивент: {eid}")
                return False

        # Уникальный ивент не должен выпасть больше 1 раза
        scurvy_count = results.get("event_scurvy_start", 0)
        if scurvy_count > 1:
            print(f"  [FAIL] Уникальный ивент выпал {scurvy_count} раз!")
            return False

        print("  [OK] Все результаты валидны, уникальный не повторялся")
        return True


def main():
    tests = [
        ("High vit_c — цинга не в пуле", test_high_vit_c),
        ("Low vit_c + day>=5 — цинга в пуле", test_low_vit_c),
        ("Low vit_c + day<5 — цинги нет", test_low_vit_c_early_day),
        ("chain_only не в дневном пуле", test_chain_only_never_daily),
        ("is_unique выдаётся 1 раз", test_unique_only_once),
        ("generate_daily_event стабильно", test_generate_stable),
    ]

    passed = 0
    for name, fn in tests:
        print(f"\n[{name}]")
        try:
            if fn():
                passed += 1
        except Exception as e:
            print(f"  [EXC] {e}")

    print(f"\n{'=' * 50}")
    print(f"Пройдено: {passed} / {len(tests)}")
    if passed == len(tests):
        print("[PASS] Все тесты движка прошли")
    else:
        print("[FAIL] Некоторые тесты упали")
        sys.exit(1)


if __name__ == "__main__":
    main()
