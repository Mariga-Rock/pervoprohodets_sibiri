"""
Достижения. Проверяются после каждого хода.

Каждое достижение выдаётся один раз. Награда — обычно мораль.
Некоторые просто фиксируют факт.
"""

ALL_ACHIEVEMENTS = {
    # ---- СТАРЫЕ (базовые) ----
    "first_city": "🏙️ Основан первый город",
    "fur_1000": "👑 1000 пушнины — дворянин",
    "fur_10000": "👑 10000 пушнины — вельможа",
    "cure_all": "💚 Все излечены от цинги",
    "travel_50": "🛤 50 вёрст пройдено",
    "lost_half": "💀 Половина отряда погибла",
    "no_deaths_50": "🛡 50 вёрст без потерь",

    # ---- МЕДИЦИНА ----
    "surgeon": "⚕️ Проведена первая ампутация",
    "no_infection": "💊 Ни одна рана не загноилась",
    "scar_witness": "🩸 Старый шрам открылся от цинги",
    "field_doctor": "✚ Пять раненых вылечено подряд",

    # ---- КАННИБАЛИЗМ ----
    "black_mark_poyarkov": "🩸 Чёрная метка Пояркова — людоедство в отряде",
    "honor_over_hunger": "🎖 Честь превыше голода — отказались от каннибализма",
    "judged_himself": "⚖ Суд над собой — казнил виновного",

    # ---- ПАНЦИРЬ ЕРМАКА ----
    "ermak_lesson": "⚓ Урок Ермака — снял царский панцирь перед Вагаем",

    # ---- ПЕЧЕНЬ БЕЛОГО МЕДВЕДЯ ----
    "barenz_curse": "☠️ Проклятие Баренца — избежали гипервитаминоза A",
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

    # ---- 1. Первый город ----
    if run.cities_count >= 1:
        if "first_city" not in user.achievements:
            _grant(user, run, "first_city", messages)
            run.morale = min(100, run.morale + 20)

    # ---- 2. 1000 пушнины ----
    if run.total_fur_sent >= 1000:
        _grant(user, run, "fur_1000", messages)

    # ---- 3. 10000 пушнины ----
    if run.total_fur_sent >= 10000:
        _grant(user, run, "fur_10000", messages)

    # ---- 4. Все излечены от цинги ----
    sick_count = sum(1 for t in run.travelers if t.alive and t.scurvy)
    if sick_count == 0 and "cure_all" not in user.achievements:
        had_scurvy = any(
            t.scurvy_refused or t.scurvy_healer_seen
            for t in run.travelers
        ) or "scar_opened" in (run.tags or [])
        if had_scurvy:
            _grant(user, run, "cure_all", messages)
            run.morale = min(100, run.morale + 10)

    # ---- 5. 50 вёрст ----
    if run.distance_covered >= 50:
        if "travel_50" not in user.achievements:
            _grant(user, run, "travel_50", messages)
            run.morale = min(100, run.morale + 10)

    # ---- 6. Потерял половину отряда ----
    alive = run.alive_count
    if alive <= 3 and "lost_half" not in user.achievements:
        _grant(user, run, "lost_half", messages)
        run.morale = max(0, run.morale - 10)

    # ---- 7. 50 вёрст без потерь ----
    if (run.distance_covered >= 50 and alive == 7
            and "no_deaths_50" not in user.achievements):
        _grant(user, run, "no_deaths_50", messages)
        run.morale = min(100, run.morale + 20)

    # ---- 8. Первая ампутация ----
    if ("amputated" in (run.tags or [])
            and "surgeon" not in user.achievements):
        _grant(user, run, "surgeon", messages)

    # ---- 9. Ни одной инфекции (30+ дней) ----
    if (run.day >= 30
            and not any(t.infection for t in run.travelers)
            and not any(t.gangrene for t in run.travelers)
            and "no_infection" not in user.achievements):
        _grant(user, run, "no_infection", messages)
        run.morale = min(100, run.morale + 10)

    # ---- 10. Шрам открылся от цинги ----
    if ("scar_opened" in (run.tags or [])
            and "scar_witness" not in user.achievements):
        _grant(user, run, "scar_witness", messages)

    # ---- 11. Полевой хирург (5 раненых вылечено) ----
    # Считаем по факту отсутствия ран + наличие шрамов
    scarred_count = sum(1 for t in run.travelers if t.alive and t.scar)
    if (scarred_count >= 5
            and "field_doctor" not in user.achievements):
        _grant(user, run, "field_doctor", messages)
        run.morale = min(100, run.morale + 10)

    # ---- 12. Чёрная метка Пояркова ----
    if run.cannibal_day > 0:
        _grant(user, run, "black_mark_poyarkov", messages)

    # ---- 13. Честь превыше голода ----
    if "refused_cannibalism" in (run.tags or []):
        _grant(user, run, "honor_over_hunger", messages)

    # ---- 14. Суд над собой ----
    if "cannibal_executed" in (run.tags or []):
        _grant(user, run, "judged_himself", messages)

    # ---- 15. Урок Ермака ----
    if (run.ermak_alive
            and run.armor_warning_given
            and not run.ermak_wearing_armor
            and run.distance_covered >= 100
            and "ermak_lesson" not in user.achievements):
        _grant(user, run, "ermak_lesson", messages)

    # ---- 16. Проклятие Баренца ----
    if ("polar_bear_done" in (run.tags or [])
            and "ate_polar_liver" not in (run.tags or [])
            and "barenz_curse" not in user.achievements):
        _grant(user, run, "barenz_curse", messages)
