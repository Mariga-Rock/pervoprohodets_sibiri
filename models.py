"""
Модели базы данных.

Две таблицы:
    User — глобальная информация об игроке (Telegram ID, счётчик смертей, DLC).
    Run  — текущая экспедиция (статы, инвентарь, теги, current_event_id).

Почему только две:
    Всё остальное (инвентарь, теги, купленные DLC) хранится в JSON-полях.
    Это даёт гибкость соло-разработчику: новый предмет не требует миграции БД.
"""

from datetime import datetime
from extensions import db


# ============================================================
# ТАБЛИЦА 1: USER (Игрок)
# Глобальная информация. Не зависит от текущей "катки".
# ============================================================
class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)

    # Telegram ID — ключ идентификации в TWA.
    # index=True — ускоряет поиск, потому что ищем по нему каждый запрос.
    telegram_id = db.Column(
        db.BigInteger,
        unique=True,
        nullable=False,
        index=True
    )

    # @username из Telegram. Может отсутствовать (у некоторых юзеров его нет).
    username = db.Column(db.String(100), nullable=True)

    # Когда игрок впервые зашёл в игру.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # ---- МЕТА-ПРОГРЕСС ----

    # Сколько раз игрок умер. Для ачивок «Умереть 10 раз», «Умереть 100 раз».
    total_deaths = db.Column(db.Integer, default=0)

    # Купленные DLC-сценарии: ["dlc_plague", "dlc_mutiny"]
    # JSON-массив. Не требует миграции при добавлении нового DLC.
    purchased_dlc = db.Column(db.JSON, default=list)

    # ---- СВЯЗЬ С ЭКСПЕДИЦИЕЙ ----
    # У игрока либо есть текущая экспедиция (Run), либо её нет.
    # Один-к-одному. cascade — при удалении User удаляется и его Run.
    run = db.relationship(
        'Run',
        backref='user',
        uselist=False,
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User {self.telegram_id}>"


# ============================================================
# ТАБЛИЦА 2: RUN (Текущая экспедиция)
# Все статы конкретной попытки выжить. Если игрок умирает — запись удаляется.
# ============================================================
class Run(db.Model):
    __tablename__ = 'runs'

    id = db.Column(db.Integer, primary_key=True)

    # Внешний ключ на User. unique=True — одна экспедиция на игрока.
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=False,
        unique=True
    )

    # ---- ЛОГИСТИКА ----
    # День в тайге (1 нажатие «Идти дальше» = 1 день).
    day = db.Column(db.Integer, default=1)

    # Пройденные вёрсты. Цель игры — 100 вёрст.
    distance_covered = db.Column(db.Integer, default=0)

    # ---- РЕСУРСЫ ВЫЖИВАНИЯ ----
    # Еда. 0 = смерть от голода.
    # 300 — стартовое значение (хватит на 15 дней при 10 людях).
    calories = db.Column(db.Integer, default=300)

    # Витамин C. Скрытый стат. <30 = цинга, <10 = смерть.
    vit_c = db.Column(db.Integer, default=100)

    # Мораль. <20 = бунт, <0 = смерть от дезертирства.
    morale = db.Column(db.Integer, default=100)

    # Тепло. Тратится на дрова. 0 = обморожения.
    warmth = db.Column(db.Integer, default=100)

    # ---- СОСТОЯНИЕ ОТРЯДА ----
    # Сколько человек живо. Влияет на расход еды и скорость.
    squad_size = db.Column(db.Integer, default=10)

    # ---- ИНВЕНТАРЬ (JSON) ----
    # {"salt": 2, "wood": 10, "lancet": 1, "herbs": 5}
    # Гибкость: добавление нового предмета НЕ требует миграции БД.
    inventory = db.Column(db.JSON, default=dict)

    # ---- ТЕГИ (JSON) ----
    # ["drank_blood", "seen_event_scurvy", "cannibals"]
    # Двигатель сюжета: игра помнит выбор игрока спустя десятки ходов.
    tags = db.Column(db.JSON, default=list)

    # ---- СОХРАНЕНИЕ СЕССИИ ----
    # Если не NULL — игрок висит в ивенте и должен сделать выбор.
    # Это решает проблему «игры в метро»: закрыл TWA, открыл — продолжил.
    current_event_id = db.Column(db.String(50), nullable=True)

    # ---- МЕТАДАННЫЕ ----
    # Последнее действие. Для аналитики (сколько игроков забросили игру).
    last_action_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<Run UserID:{self.user_id} Day:{self.day}>"
