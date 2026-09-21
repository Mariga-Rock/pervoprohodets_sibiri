"""
Достижения. Проверяются после каждого хода.

Каждое достижение выдаётся один раз. Награда — обычно мораль.
Некоторые просто фиксируют факт (титул дворянина уже выдан в next_turn).
"""

ALL_ACHIEVEMENTS = {
    "first_city": "🏙️ Основан первый город",
    "fur_1000": "👑 1000 пушнины — дворянин",
    "fur_10000": "👑 10000 пушнины — вельможа",
    "cure_all": "💚 Все излечены от цинги",
    "travel_50": "🛤 50 вёрст пройдено",
    "lost_half": "💀 Половина отряда погибла",
    "no_deaths_50": "🛡 50 вёрст без потерь",
}


def _grant(user, run, key, messages):
    """Выдаёт достижение, если его ещё нет."""
    if key in (user.achievements or []):
        return
    user.achievements = list(user.achievements or []) + [key]
    messages.append(ALL_ACHIEVEMENTS.get(key, key))


def check_achievements(user, run, messages):
    """
    Проверяет все условия. Записывает в messages список полученных достижений.
    Мутирует user.achievements и run.morale.
    """
    if user.achievements is None:
        user.achievements = []

    # 1. Первый город
    if run.cities_count >= 1:
        _grant(user, run, "first_city", messages)
        run.morale = min(100, run.morale + 20)

    # 2. 1000 пушнины
    if run.total_fur_sent >= 1000:
        _grant(user, run, "fur_1000", messages)

    # 3. 10000 пушнины
    if run.total_fur_sent >= 10000:
        _grant(user, run, "fur_10000", messages)

    # 4. Все излечены от цинги
    sick_count = sum(1 for t in run.travelers if t.alive and t.scurvy)
    if sick_count == 0 and "cure_all" not in user.achievements:
        # Условие: хотя бы один случай цинги был за игру (тег healer_pending, cure, и т.д.)
        had_scurvy = any(
            t.scurvy_refused or t.scurvy_healer_seen
            for t in run.travelers
        ) or "cure_scurvy_hero" in (run.tags or [])
        if had_scurvy:
            _grant(user, run, "cure_all", messages)
            run.morale = min(100, run.morale + 10)

    # 5. 50 вёрст
    if run.distance_covered >= 50:
        _grant(user, run, "travel_50", messages)
        run.morale = min(100, run.morale + 10)

    # 6. Потерял половину отряда
    alive = run.alive_count
    if alive <= 3 and "lost_half" not in user.achievements:
        _grant(user, run, "lost_half", messages)
        run.morale = max(0, run.morale - 10)

    # 7. 50 вёрст без потерь
    # Считаем: у нас изначально 7 бойцов. Если живо 7 и прошли 50 — награда.
    if (run.distance_covered >= 50 and alive == 7
            and "no_deaths_50" not in user.achievements):
        _grant(user, run, "no_deaths_50", messages)
        run.morale = min(100, run.morale + 20)
