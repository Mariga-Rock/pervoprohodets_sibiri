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
