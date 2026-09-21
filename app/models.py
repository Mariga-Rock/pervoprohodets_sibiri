"""Модели базы данных. User, Run, Traveler."""
from datetime import datetime
from app.extensions import db


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    telegram_id = db.Column(
        db.BigInteger, unique=True, nullable=False, index=True
    )
    username = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    total_deaths = db.Column(db.Integer, default=0)
    purchased_dlc = db.Column(db.JSON, default=list)
    achievements = db.Column(db.JSON, default=list)

    run = db.relationship(
        'Run', backref='user', uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User {self.telegram_id}>"


class Run(db.Model):
    __tablename__ = 'runs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True
    )

    # ---- ОСНОВНОЕ ----
    day = db.Column(db.Integer, default=1)
    distance_covered = db.Column(db.Integer, default=0)

    # ---- ПРОВИЗИЯ ----
    flour = db.Column(db.Integer, default=300)
    fish = db.Column(db.Integer, default=0)
    meat = db.Column(db.Integer, default=0)
    cranberries = db.Column(db.Integer, default=0)
    hunger_days = db.Column(db.Integer, default=0)

    # ---- СТАТЫ ----
    vit_c = db.Column(db.Integer, default=100)
    morale = db.Column(db.Integer, default=100)
    warmth = db.Column(db.Integer, default=100)
    discipline = db.Column(db.Integer, default=70)

    # ---- ЭКОНОМИКА ----
    money = db.Column(db.Integer, default=0)
    charters = db.Column(db.Integer, default=0)
    total_fur_sent = db.Column(db.Integer, default=0)
    cities_count = db.Column(db.Integer, default=0)
    noble_title = db.Column(db.String(32), nullable=True)

    # ---- СЮЖЕТНЫЕ ФЛАГИ ----
    # Искер: none / taken / under_siege / relieved / abandoned
    isker_status = db.Column(db.String(20), default="none")
    # Сколько дней осады осталось (0 если не в осаде)
    siege_days_left = db.Column(db.Integer, default=0)
    # Итог осады: none / karacha_left / broke_through
    siege_result = db.Column(db.String(20), default="none")
    # Живы ли ключевые персонажи
    ivan_koltso_alive = db.Column(db.Boolean, default=True)
    ermak_alive = db.Column(db.Boolean, default=True)
    # Кто ведёт отряд: ermak / meshcheryak
    leader = db.Column(db.String(20), default="ermak")
    # Слухи о Мангазее (0..5)
    mangazeya_rumors = db.Column(db.Integer, default=0)
    # Ясак: сколько племён присягнуло (0..5)
    yasak_count = db.Column(db.Integer, default=0)
    # Волховский
    volhovsky_arrived = db.Column(db.Boolean, default=False)
    volhovsky_alive = db.Column(db.Boolean, default=False)
    volhovsky_healed = db.Column(db.Boolean, default=False)

    # ---- СЛУЖЕБНОЕ ----
    has_priest = db.Column(db.Boolean, default=True)
    last_advisor_day = db.Column(db.Integer, default=0)

    # ---- ИНВЕНТАРЬ И ТЕГИ ----
    inventory = db.Column(db.JSON, default=dict)
    tags = db.Column(db.JSON, default=list)
    recent_events = db.Column(db.JSON, default=list)

    current_event_id = db.Column(db.String(50), nullable=True)
    last_action_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    travelers = db.relationship(
        'Traveler',
        backref='run',
        cascade='all, delete-orphan',
        lazy='select',
    )

    # ---- ВЫЧИСЛЯЕМЫЕ ПОЛЯ ----

    @property
    def squad_size(self):
        """Сколько бойцов могут идти (живые, не раненые, не сиделки)."""
        return sum(
            1 for t in self.travelers
            if t.alive and not t.wounded and not t.is_caretaker
        )

    @property
    def wounded(self):
        """Сколько раненых."""
        return sum(
            1 for t in self.travelers
            if t.alive and t.wounded
        )

    @property
    def caretaker_count(self):
        """Сколько сиделок при раненых."""
        return sum(
            1 for t in self.travelers
            if t.alive and t.is_caretaker
        )

    @property
    def alive_count(self):
        """Всего живых (включая раненых и сиделок)."""
        return sum(1 for t in self.travelers if t.alive)

    def __repr__(self):
        return f"<Run UserID:{self.user_id} Day:{self.day}>"


class Traveler(db.Model):
    __tablename__ = 'travelers'

    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(
        db.Integer, db.ForeignKey('runs.id'), nullable=False, index=True
    )

    name = db.Column(db.String(64), nullable=False)

    hunting = db.Column(db.Integer, default=4)
    endurance_max = db.Column(db.Integer, default=5)
    endurance = db.Column(db.Integer, default=5)

    is_doctor = db.Column(db.Boolean, default=False)
    is_scientist = db.Column(db.Boolean, default=False)
    is_ataman = db.Column(db.Boolean, default=False)
    is_priest = db.Column(db.Boolean, default=False)

    wounded = db.Column(db.Boolean, default=False)
    wounded_days_left = db.Column(db.Integer, default=0)

    is_caretaker = db.Column(db.Boolean, default=False)
    caring_for = db.Column(db.String(64), nullable=True)

    scurvy = db.Column(db.Boolean, default=False)
    scurvy_refused = db.Column(db.Boolean, default=False)
    scurvy_healer_seen = db.Column(db.Boolean, default=False)

    alive = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"<Traveler {self.name} end={self.endurance}>"
