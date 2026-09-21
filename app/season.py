"""
Сезоны и витамин C.

Сезон: 15 дней. Весна → лето → осень → зима → весна.
Витамин C: ступенчатая деградация. Через 56 дней — цинга.
"""
from app.constants import (
    SEASON_LENGTH, SEASON_NAMES,
    HUNT_MOD, FISH_MOD, HERBS_MOD,
    VIT_DEGRADATION_SLOW, VIT_DEGRADATION_MED, VIT_DEGRADATION_FAST,
    VIT_SLOW_UNTIL, VIT_MED_UNTIL,
)


def advance_season(run):
    """
    Увеличивает день сезона. Если сезон кончился — переключает.
    Возвращает имя нового сезона или None, если смены не было.
    """
    run.season_day += 1
    if run.season_day > SEASON_LENGTH:
        run.season_day = 1
        run.season = (run.season + 1) % 4
        return SEASON_NAMES[run.season]
    return None


def season_name(run):
    return SEASON_NAMES.get(run.season, "?")


def degrade_vit_c(run):
    """
    Ступенчатая деградация витамина C.
    Счётчик days_without_vit увеличивается на 1.
    vit_c падает со скоростью, зависящей от счётчика.
    """
    run.days_without_vit += 1

    if run.days_without_vit <= VIT_SLOW_UNTIL:
        loss = VIT_DEGRADATION_SLOW
    elif run.days_without_vit <= VIT_MED_UNTIL:
        loss = VIT_DEGRADATION_MED
    else:
        loss = VIT_DEGRADATION_FAST

    run.vit_c = max(0, run.vit_c - loss)


def add_vitamin(run, amount):
    """
    Игрок получил источник витамина C.
    Сбрасывает счётчик дней без витамина, добавляет vit_c.
    Цинга начинает отступать.
    """
    run.vit_c = min(100, run.vit_c + amount)
    run.days_without_vit = 0
    if run.scurvy_active:
        run.scurvy_active = False


def get_hunt_modifier(run):
    return HUNT_MOD.get(run.season, 1.0)


def get_fish_modifier(run):
    return FISH_MOD.get(run.season, 1.0)


def get_herbs_modifier(run):
    return HERBS_MOD.get(run.season, 1.0)


def can_gather_berries(run):
    """Ягоды доступны летом и осенью."""
    return run.season in (1, 2)


def can_use_cherem(run):
    """Черемша растёт весной и летом."""
    return run.season in (0, 1)
