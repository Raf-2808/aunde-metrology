"""Relacyjny model. Konfiguracje i wyniki zatwierdzone pozostają niezmienne."""

import os
from datetime import datetime, timezone
from sqlalchemy import (
    create_engine,
    String,
    Integer,
    Text,
    ForeignKey,
    UniqueConstraint,
    JSON,
    Boolean,
    DateTime,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


def teraz():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


engine = create_engine(
    os.environ.get("DATABASE_URL", "sqlite:///./lims.db"), pool_pre_ping=True
)
Session = sessionmaker(engine, expire_on_commit=False)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(String(120), unique=True)
    password: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(30))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class LoginSession(Base):
    __tablename__ = "login_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    expires: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    csrf: Mapped[str] = mapped_column(String(80))
    scopes: Mapped[dict] = mapped_column(JSON, default=dict)


class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(200), index=True)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=teraz)


class Method(Base):
    __tablename__ = "methods"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(120), unique=True)
    name: Mapped[str] = mapped_column(Text)


class Article(Base):
    __tablename__ = "articles"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(Text)
    cycle: Mapped[int] = mapped_column(Integer, default=0)


class Config(Base):
    __tablename__ = "article_configs"
    __table_args__ = (UniqueConstraint("article_id", "version"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    author: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=teraz)


class Characteristic(Base):
    __tablename__ = "characteristics"
    __table_args__ = (UniqueConstraint("config_id", "key"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    config_id: Mapped[int] = mapped_column(ForeignKey("article_configs.id"), index=True)
    method_id: Mapped[int] = mapped_column(ForeignKey("methods.id"))
    key: Mapped[str] = mapped_column(String(40))
    position: Mapped[int] = mapped_column(Integer)
    spec: Mapped[dict] = mapped_column(JSON)


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (UniqueConstraint("article_id", "lot", "roll"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id"), index=True)
    lot: Mapped[str] = mapped_column(String(120), index=True)
    roll: Mapped[str] = mapped_column(String(120), default="")
    quantity: Mapped[str] = mapped_column(String(80), default="")
    reporter: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=teraz)
    completed: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(30), default="WAITING")
    required_sessions: Mapped[int] = mapped_column(Integer, default=1)
    extra: Mapped[list] = mapped_column(JSON, default=list)


class LabSession(Base):
    __tablename__ = "lab_sessions"
    __table_args__ = (
        UniqueConstraint("article_id", "cycle", "revision"),
        UniqueConstraint("correction_of"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id"), index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    config_id: Mapped[int] = mapped_column(ForeignKey("article_configs.id"))
    cycle: Mapped[int] = mapped_column(Integer)
    revision: Mapped[int] = mapped_column(Integer, default=0)
    operator: Mapped[int] = mapped_column(ForeignKey("users.id"))
    test_date: Mapped[str] = mapped_column(String(10))
    metadata_: Mapped[dict] = mapped_column("metadata", JSON)
    ok: Mapped[bool] = mapped_column(Boolean)
    acknowledged: Mapped[bool] = mapped_column(Boolean)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=teraz)
    correction_of: Mapped[int | None] = mapped_column(
        ForeignKey("lab_sessions.id"), nullable=True
    )
    reason: Mapped[str] = mapped_column(Text, default="")


class Result(Base):
    __tablename__ = "results"
    __table_args__ = (UniqueConstraint("session_id", "characteristic_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("lab_sessions.id"), index=True)
    characteristic_id: Mapped[int] = mapped_column(ForeignKey("characteristics.id"))
    average: Mapped[str | None] = mapped_column(Text, nullable=True)
    ok: Mapped[bool] = mapped_column(Boolean)
    simulated_average: Mapped[str | None] = mapped_column(Text, nullable=True)
    simulated_ok: Mapped[bool] = mapped_column(Boolean)


class Measurement(Base):
    __tablename__ = "measurements"
    __table_args__ = (UniqueConstraint("result_id", "position"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    result_id: Mapped[int] = mapped_column(ForeignKey("results.id"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    value: Mapped[str] = mapped_column(Text)
    ok: Mapped[bool] = mapped_column(Boolean)


class Simulation(Base):
    __tablename__ = "simulations"
    measurement_id: Mapped[int] = mapped_column(
        ForeignKey("measurements.id"), primary_key=True
    )
    value: Mapped[str] = mapped_column(Text)
    ok: Mapped[bool] = mapped_column(Boolean)
    corrected: Mapped[bool] = mapped_column(Boolean)
    algorithm: Mapped[str] = mapped_column(String(30), default="inward-5pct-v1")
    parameters: Mapped[dict] = mapped_column(JSON)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=teraz)


class Disposition(Base):
    __tablename__ = "dispositions"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    author: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=teraz)
    held: Mapped[bool] = mapped_column(Boolean)
    reason: Mapped[str] = mapped_column(Text)


class SpcConfig(Base):
    __tablename__ = "spc_configs"
    id: Mapped[int] = mapped_column(primary_key=True)
    characteristic_id: Mapped[int] = mapped_column(
        ForeignKey("characteristics.id"), index=True
    )
    limits: Mapped[dict] = mapped_column(JSON)
    sampling_plan: Mapped[str] = mapped_column(Text)
    author: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=teraz)


class NotificationRule(Base):
    __tablename__ = "notification_rules"
    id: Mapped[int] = mapped_column(primary_key=True)
    characteristic_id: Mapped[int] = mapped_column(ForeignKey("characteristics.id"))
    email: Mapped[str] = mapped_column(String(254))
    events: Mapped[list] = mapped_column(JSON)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (UniqueConstraint("session_id", "spc_config_id", "event"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("lab_sessions.id"))
    spc_config_id: Mapped[int] = mapped_column(ForeignKey("spc_configs.id"))
    event: Mapped[str] = mapped_column(String(40))
    payload: Mapped[dict] = mapped_column(JSON)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=teraz)


class Outbox(Base):
    __tablename__ = "mail_outbox"
    __table_args__ = (UniqueConstraint("alert_id", "recipient"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey("alerts.id"))
    recipient: Mapped[str] = mapped_column(String(254))
    status: Mapped[str] = mapped_column(String(30), default="PENDING")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error: Mapped[str] = mapped_column(Text, default="")


class Audit(Base):
    __tablename__ = "audit"
    id: Mapped[int] = mapped_column(primary_key=True)
    author: Mapped[int] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(80))
    entity: Mapped[str] = mapped_column(String(80))
    payload: Mapped[dict] = mapped_column(JSON)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=teraz)


class HistoricalRow(Base):
    __tablename__ = "historical_rows"
    __table_args__ = (UniqueConstraint("file_hash", "row_number"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    file_hash: Mapped[str] = mapped_column(String(64))
    row_number: Mapped[int] = mapped_column(Integer)
    lot: Mapped[str] = mapped_column(String(120), index=True)
    values: Mapped[dict] = mapped_column(JSON)
    issues: Mapped[list] = mapped_column(JSON)
    author: Mapped[int] = mapped_column(ForeignKey("users.id"))
