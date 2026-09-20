"""Модели базы данных. User и Run."""
from datetime import datetime
from app.extensions import db
from app.constants import (
    DEFAULT_CALORIES, DEFAULT_VIT_C, DEFAULT_MORALE, DEFAULT_WARMTH,
    DEFAULT_SQUAD_SIZE, DEFAULT_DAY, DEFAULT_DISTANCE, DEFAULT_INVENTORY,
)


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

    day = db.Column(db.Integer, default=DEFAULT_DAY)
    distance_covered = db.Column(db.Integer, default=DEFAULT_DISTANCE)

    calories = db.Column(db.Integer, default=DEFAULT_CALORIES)
    vit_c = db.Column(db.Integer, default=DEFAULT_VIT_C)
    morale = db.Column(db.Integer, default=DEFAULT_MORALE)
    warmth = db.Column(db.Integer, default=DEFAULT_WARMTH)

    squad_size = db.Column(db.Integer, default=DEFAULT_SQUAD_SIZE)

    inventory = db.Column(db.JSON, default=lambda: dict(DEFAULT_INVENTORY))
    tags = db.Column(db.JSON, default=list)

    current_event_id = db.Column(db.String(50), nullable=True)

    last_action_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<Run UserID:{self.user_id} Day:{self.day}>"
