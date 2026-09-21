"""
Создать или сбросить тестового игрока.

Запуск:
    python scripts/seed_test_player.py
    python scripts/seed_test_player.py --tg 555
    python scripts/seed_test_player.py --tg 555 --no-run

По умолчанию создаёт:
    telegram_id      = 123123123
    vit_c            = 100
    current_event_id = None
    отряд            = STARTING_TRAVELERS (7 бойцов)

Если игрок уже есть — удаляет его и создаёт заново.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from app.extensions import db
from app.models import User, Run, Traveler
from app.constants import (
    DEFAULT_CRANBERRIES,
    DEFAULT_DAY,
    DEFAULT_DISTANCE,
    DEFAULT_FISH,
    DEFAULT_FLOUR,
    DEFAULT_INVENTORY,
    DEFAULT_MEAT,
    DEFAULT_MORALE,
    DEFAULT_VIT_C,
    DEFAULT_WARMTH,
    STARTING_TRAVELERS,
)


def seed(tg_id: int, create_run: bool = True):
    app = create_app()
    with app.app_context():
        # Удаляем старого
        old = User.query.filter_by(telegram_id=tg_id).first()
        if old:
            db.session.delete(old)
            db.session.commit()

        user = User(telegram_id=tg_id, username="tester")
        db.session.add(user)
        db.session.flush()

        if not create_run:
            db.session.commit()
            print(f"[OK] Игрок {tg_id} создан без экспедиции")
            return

        run = Run(
            user_id=user.id,
            day=DEFAULT_DAY,
            distance_covered=DEFAULT_DISTANCE,
            flour=DEFAULT_FLOUR,
            fish=DEFAULT_FISH,
            meat=DEFAULT_MEAT,
            cranberries=DEFAULT_CRANBERRIES,
            vit_c=DEFAULT_VIT_C,
            morale=DEFAULT_MORALE,
            warmth=DEFAULT_WARMTH,
            inventory=dict(DEFAULT_INVENTORY),
            tags=[],
            recent_events=[],
            current_event_id=None,
        )
        db.session.add(run)
        db.session.flush()

        for tpl in STARTING_TRAVELERS:
            t = Traveler(
                run_id=run.id,
                name=tpl["name"],
                hunting=tpl["hunting"],
                endurance_max=tpl["endurance_max"],
                endurance=tpl["endurance_max"],
                is_doctor=tpl["is_doctor"],
                is_scientist=tpl["is_scientist"],
                is_ataman=tpl["is_ataman"],
                is_priest=tpl.get("is_priest", False),
                alive=True,
                wounded=False,
                is_caretaker=False,
                scurvy=False,
            )
            db.session.add(t)

        db.session.commit()

        print(f"[OK] Тестовый игрок создан")
        print(f"     telegram_id      = {user.telegram_id}")
        print(f"     run.id           = {run.id}")
        print(f"     day              = {run.day}")
        print(f"     flour            = {run.flour}")
        print(f"     fish             = {run.fish}")
        print(f"     meat             = {run.meat}")
        print(f"     vit_c            = {run.vit_c}")
        print(f"     morale           = {run.morale}")
        print(f"     money            = {run.money}")
        print(f"     charters         = {run.charters}")
        print(f"     current_event_id = {run.current_event_id}")
        print(f"     отряд            = {len(STARTING_TRAVELERS)} бойцов:")
        for t in run.travelers:
            role = ""
            if t.is_ataman:
                role = " (атаман)"
            elif t.is_priest:
                role = " (священник)"
            elif t.is_doctor:
                role = " (лекарь)"
            print(
                f"       - {t.name}{role}: "
                f"hunting={t.hunting}, endurance={t.endurance}/{t.endurance_max}"
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tg", type=int, default=123123123,
                        help="telegram_id тестового игрока")
    parser.add_argument("--no-run", action="store_true",
                        help="создать только User, без Run")
    args = parser.parse_args()

    seed(args.tg, create_run=not args.no_run)
