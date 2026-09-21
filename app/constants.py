"""
Игровые константы.
"""

# ---- СТАРТОВЫЕ СТАТЫ ЭКСПЕДИЦИИ ----
DEFAULT_DAY = 1
DEFAULT_DISTANCE = 0
DEFAULT_VIT_C = 100
DEFAULT_MORALE = 100
DEFAULT_WARMTH = 100
DEFAULT_SQUAD_SIZE = 10

# ---- ПРОВИЗИЯ ----
DEFAULT_FLOUR = 300
DEFAULT_FISH = 0
DEFAULT_MEAT = 0
DEFAULT_CRANBERRIES = 0

# Сколько провизии съедает один человек за день.
DAILY_FOOD_PER_PERSON = 2

# Сколько дней голода до смерти.
HUNGER_DEATH_DAY = 30

# Сколько даёт рыбалка и охота за день.
FISH_PER_DAY = (2, 5)
MEAT_PER_DAY = (2, 4)

# ---- СТАРТОВЫЙ ИНВЕНТАРЬ ----
DEFAULT_INVENTORY = {
    "salt": 1,
    "lancet": 1,
    "herbs": 3,
    "wood": 10,
}

# ---- ЛИМИТЫ СТАТОВ ----
MAX_CALORIES = 300
MAX_VIT_C = 100
MAX_MORALE = 100
MAX_WARMTH = 100

# ---- ЦЕЛЬ ИГРЫ ----
TARGET_DISTANCE = 100

# ---- ПОРОГИ КРИЗИСОВ ----
SCURVY_STAGE_1 = 30
SCURVY_STAGE_2 = 10
MORALE_MUTINY = 20
HUNGER_DEATH_DAYS = 3

# ---- ЦИНГА ----
SCURVY_HEALER_DELAY = 3
SCURVY_ENDURANCE_LOSS = 1

# ---- ЭКОНОМИКА ----
FUR_PRICE = 5
FUR_PER_CHARTER = 100


def city_charter_cost(cities_count):
    """Сколько грамот нужно на основание нового города."""
    return 5 + 5 * cities_count


# ---- ТИТУЛЫ И ПЬЯНСТВО ----
TITLE_NOBLE_THRESHOLD = 1000
TITLE_MAGNATE_THRESHOLD = 10000
DRUNKARD_MONEY_THRESHOLD = 2000


# ---- СИНЕРГИЯ ----
def hunting_synergy(n):
    """Чем больше людей — тем продуктивнее охота."""
    if n <= 0:
        return 0.0
    if n == 1:
        return 1.0
    return 1.0 + 0.4 * (n - 1)


# ---- СТАРТОВЫЙ ОТРЯД ----
STARTING_TRAVELERS = [
    {
        "name": "Ермак Тимофеевич",
        "hunting": 6, "endurance_max": 6,
        "is_ataman": True, "is_doctor": False, "is_scientist": False,
    },
    {
        "name": "Иван Кольцо",
        "hunting": 5, "endurance_max": 6,
        "is_ataman": True, "is_doctor": False, "is_scientist": False,
    },
    {
        "name": "Матвей Мещеряк",
        "hunting": 5, "endurance_max": 6,
        "is_ataman": True, "is_doctor": False, "is_scientist": False,
    },
    {
        "name": "Никита Пан",
        "hunting": 6, "endurance_max": 6,
        "is_ataman": True, "is_doctor": False, "is_scientist": False,
    },
    {
        "name": "Богдан Брязга",
        "hunting": 4, "endurance_max": 6,
        "is_ataman": True, "is_doctor": False, "is_scientist": False,
    },
    {
        "name": "Остап",
        "hunting": 4, "endurance_max": 4,
        "is_ataman": False, "is_doctor": False, "is_scientist": False,
    },
    {
        "name": "Отец Никифор",
        "hunting": 2, "endurance_max": 5,
        "is_ataman": False, "is_doctor": True, "is_scientist": False,
        "is_priest": True,
    },
]

# ============================================================
# СЕЗОНЫ И ГОД
# ============================================================
SEASON_LENGTH = 7  # 7 дней = 1 сезон, 28 дней = 1 год
SEASON_SPRING = 0
SEASON_SUMMER = 1
SEASON_AUTUMN = 2
SEASON_WINTER = 3

SEASON_NAMES = {
    0: "Весна",
    1: "Лето",
    2: "Осень",
    3: "Зима",
}

# Сколько вёрст отряд проходит за день в каждый сезон.
# Зимой — 0. Полный стоп.
SPEED_BY_SEASON = {
    0: 2,  # весна — распутица
    1: 3,  # лето
    2: 2,  # осень
    3: 0,  # зима
}

# Модификаторы охоты по сезонам
HUNT_MOD = {
    0: 1.0,   # весна
    1: 1.2,   # лето
    2: 1.3,   # осень — лучшее время
    3: 0.5,   # зима — плохо
}

# Модификаторы рыбалки по сезонам
FISH_MOD = {
    0: 0.5,   # весна — лёд сходит
    1: 1.5,   # лето — лучшее время
    2: 1.2,   # осень — клёв хороший
    3: 0.3,   # зима — подлёдный лов, мало
}

# Модификаторы сбора трав по сезонам
HERBS_MOD = {
    0: 1.3,   # весна — всё растёт
    1: 1.5,   # лето
    2: 0.8,   # осень — увядает
    3: 0.2,   # зима — почти нет
}

# ============================================================
# ВИТАМИН C — СТУПЕНЧАТАЯ ДЕГРАДАЦИЯ
# ============================================================
# Дни без источника витамина → скорость падения vit_c в день
VIT_DEGRADATION_SLOW = 1    # 0–28 дней
VIT_DEGRADATION_MED = 3     # 29–56 дней
VIT_DEGRADATION_FAST = 6    # 57+ дней

VIT_SLOW_UNTIL = 28
VIT_MED_UNTIL = 56

# Через сколько дней без витамина начинается цинга
SCURVY_START_DAYS = 56

# Через сколько дней с источником витамина цинга проходит
SCURVY_RECOVERY_DAYS = 3

# ============================================================
# ИСТОЧНИКИ ВИТАМИНА C
# ============================================================
VIT_FROM_PINE = 15       # хвойный отвар — всегда
VIT_FROM_FISH = 5        # при рыбалке
VIT_FROM_BERRIES = 12    # ягоды (лето/осень)
VIT_FROM_CHEREM = 45     # черемша (весна/лето)
VIT_FROM_MEAT = 3        # при охоте
VIT_FROM_RAW_FISH = 8    # если есть рыба и решено есть сырой
