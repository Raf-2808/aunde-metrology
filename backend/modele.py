"""Typowane encje ewidencji; historia pozostaje przy archiwizacji."""

from datetime import date, datetime, timezone
from uuid import uuid4
from sqlalchemy import (
    String,
    Text,
    DateTime,
    Date,
    ForeignKey,
    Integer,
    Boolean,
    JSON,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# Generuje trwały UUID tekstowy dla nowego rekordu; bez skutków ubocznych.
def nowy_id() -> str:
    return str(uuid4())


# Zwraca bieżący czas UTC dla zapisu zdarzenia.
def teraz_utc() -> datetime:
    return datetime.now(timezone.utc)


class Baza(DeclarativeBase):
    pass


class Uzytkownik(Baza):
    __tablename__ = "uzytkownicy"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=nowy_id)
    login: Mapped[str] = mapped_column(String(150), unique=True)
    skrot_hasla: Mapped[str] = mapped_column(Text)
    rola: Mapped[str] = mapped_column(String(20))
    aktywny: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (CheckConstraint("rola IN ('Viewer','Editor','Administrator')"),)


class Sesja(Baza):
    __tablename__ = "sesje"
    skrot: Mapped[str] = mapped_column(String(64), primary_key=True)
    uzytkownik_id: Mapped[str] = mapped_column(ForeignKey("uzytkownicy.id"))
    csrf: Mapped[str] = mapped_column(String(64))
    wygasa: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class TypPrzyrzadu(Baza):
    __tablename__ = "typy_przyrzadow"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=nowy_id)
    nazwa: Mapped[str] = mapped_column(String(250), unique=True)


class Wydzial(Baza):
    __tablename__ = "wydzialy"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=nowy_id)
    nazwa: Mapped[str] = mapped_column(String(150), unique=True)


class Przyrzad(Baza):
    __tablename__ = "przyrzady"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=nowy_id)
    numer: Mapped[str] = mapped_column(Text, index=True)
    typ_id: Mapped[str] = mapped_column(ForeignKey("typy_przyrzadow.id"), index=True)
    klasa: Mapped[str] = mapped_column(String(1), default="B", server_default="B", index=True)
    stan: Mapped[str] = mapped_column(String(30), default="Na stanie", index=True)
    status: Mapped[str] = mapped_column(String(30), default="Nieaktywna", index=True)
    odblokowany: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    stan_techniczny: Mapped[str] = mapped_column(String(40), default="Nieustalony")
    komentarz_dat: Mapped[str | None] = mapped_column(String(100), nullable=True)
    wersja: Mapped[int] = mapped_column(Integer, default=1)
    usunieto_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    __table_args__ = (
        UniqueConstraint("numer", name="unikalny_numer_przyrzadu"),
        CheckConstraint("klasa IN ('A','B','C')"),
        CheckConstraint("status IN ('Aktywna','Nieaktywna')"),
        CheckConstraint("stan IN ('Na stanie','Zwrócona')"),
    )


class Przydzial(Baza):
    __tablename__ = "przydzialy"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=nowy_id)
    przyrzad_id: Mapped[str] = mapped_column(ForeignKey("przyrzady.id"), index=True)
    wydzial_id: Mapped[str] = mapped_column(ForeignKey("wydzialy.id"))
    od_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=teraz_utc)
    do_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DaneRR(Baza):
    __tablename__ = "dane_rr"
    przyrzad_id: Mapped[str] = mapped_column(ForeignKey("przyrzady.id"), primary_key=True)
    wartosc: Mapped[str] = mapped_column(String(20), default="---")


class Harmonogram(Baza):
    __tablename__ = "harmonogramy"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=nowy_id)
    przyrzad_id: Mapped[str] = mapped_column(ForeignKey("przyrzady.id"), index=True)
    proces: Mapped[str] = mapped_column(String(20))
    ostatni: Mapped[date | None] = mapped_column(Date, nullable=True)
    interwal: Mapped[int] = mapped_column(Integer, default=12)
    jednostka: Mapped[str] = mapped_column(String(15), default="miesiac")
    termin_zrodlowy: Mapped[date | None] = mapped_column(Date, nullable=True)
    nadpisanie: Mapped[date | None] = mapped_column(Date, nullable=True)
    uzasadnienie: Mapped[str | None] = mapped_column(Text, nullable=True)
    wynik: Mapped[str | None] = mapped_column(String(20), nullable=True)
    __table_args__ = (
        UniqueConstraint("przyrzad_id", "proces"),
        CheckConstraint("interwal > 0 AND interwal <= 12000"),
        CheckConstraint("proces IN ('sprawdzenie','wzorcowanie')"),
        CheckConstraint("jednostka IN ('dzien','miesiac','rok')"),
    )


class Sprawdzenie(Baza):
    __tablename__ = "sprawdzenia"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=nowy_id)
    przyrzad_id: Mapped[str] = mapped_column(ForeignKey("przyrzady.id"), index=True)
    data_wykonania: Mapped[date] = mapped_column(Date)
    wynik: Mapped[str | None] = mapped_column(String(20), nullable=True)
    uwagi: Mapped[str] = mapped_column(Text, default="")
    uzytkownik_id: Mapped[str | None] = mapped_column(ForeignKey("uzytkownicy.id"), nullable=True)


class Wzorcowanie(Baza):
    __tablename__ = "wzorcowania"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=nowy_id)
    przyrzad_id: Mapped[str] = mapped_column(ForeignKey("przyrzady.id"), index=True)
    data_wykonania: Mapped[date] = mapped_column(Date)
    wynik: Mapped[str | None] = mapped_column(String(20), nullable=True)
    numer_swiadectwa: Mapped[str] = mapped_column(Text, default="")
    uzytkownik_id: Mapped[str | None] = mapped_column(ForeignKey("uzytkownicy.id"), nullable=True)


class LinkQR(Baza):
    __tablename__ = "linki_qr"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=nowy_id)
    przyrzad_id: Mapped[str] = mapped_column(ForeignKey("przyrzady.id"), index=True)
    token: Mapped[str] = mapped_column(String(100), unique=True)
    uniewazniono_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OdczytQR(Baza):
    __tablename__ = "odczyty_qr"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    przyrzad_id: Mapped[str] = mapped_column(ForeignKey("przyrzady.id"), index=True)
    link_id: Mapped[str] = mapped_column(ForeignKey("linki_qr.id"))
    czas: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=teraz_utc, index=True)
    zrodlo: Mapped[str] = mapped_column(String(10), default="QR")
    wynik: Mapped[str] = mapped_column(String(20), default="Sukces")
    migawka: Mapped[dict] = mapped_column(JSON)


class HistoriaStatusu(Baza):
    __tablename__ = "historia_statusow"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=nowy_id)
    przyrzad_id: Mapped[str] = mapped_column(ForeignKey("przyrzady.id"), index=True)
    pole: Mapped[str] = mapped_column(String(40))
    przed: Mapped[str] = mapped_column(Text)
    po: Mapped[str] = mapped_column(Text)
    czas: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=teraz_utc)


class Audyt(Baza):
    __tablename__ = "audyt"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=nowy_id)
    uzytkownik_id: Mapped[str | None] = mapped_column(ForeignKey("uzytkownicy.id"), nullable=True)
    rekord_id: Mapped[str] = mapped_column(String(36), index=True)
    operacja: Mapped[str] = mapped_column(String(50))
    szczegoly: Mapped[dict] = mapped_column(JSON)
    czas: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=teraz_utc)


class Import(Baza):
    __tablename__ = "importy"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=nowy_id)
    sha256: Mapped[str] = mapped_column(String(64), unique=True)
    czas: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=teraz_utc)


class WierszImportu(Baza):
    __tablename__ = "wiersze_importu"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=nowy_id)
    import_id: Mapped[str] = mapped_column(ForeignKey("importy.id"))
    wiersz: Mapped[int] = mapped_column(Integer)
    przyrzad_id: Mapped[str | None] = mapped_column(ForeignKey("przyrzady.id"), nullable=True)
    surowe: Mapped[dict] = mapped_column(JSON)
    problemy: Mapped[list] = mapped_column(JSON)
    __table_args__ = (UniqueConstraint("import_id", "wiersz"),)


class Powiadomienie(Baza):
    __tablename__ = "powiadomienia_email"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=nowy_id)
    klucz: Mapped[str] = mapped_column(String(180), unique=True)
    przyrzad_id: Mapped[str] = mapped_column(ForeignKey("przyrzady.id"))
    odbiorca: Mapped[str] = mapped_column(String(150), default="jakosc@aunde.pl")
    dane: Mapped[dict] = mapped_column(JSON)
    wyslano_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    proby: Mapped[int] = mapped_column(Integer, default=0)
    nastepna_proba_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=teraz_utc)
    blad: Mapped[str | None] = mapped_column(String(100), nullable=True)
