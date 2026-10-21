"""Reguły ewidencji niezależne od HTTP i bazy danych."""

from calendar import monthrange
from datetime import date
import re

ULICE = ("Wersalska", "Senatorska", "Kaczeńcowa")


# Zwraca nazwę wydziału bez rozpoznanej ulicy; zachowuje pozostałe słowa, bez skutków ubocznych.
def normalizuj_wydzial(nazwa: str) -> str:
    wynik = " ".join(nazwa.split())
    for ulica in ULICE:
        wynik = re.sub(
            r"\s+(?:(?:ul(?:ica)?\.?)\s+)?"
            + re.escape(ulica)
            + r"(?:\s+\d+[a-z]?(?:[/-]\d+[a-z]?)?)?$",
            "",
            wynik,
            flags=re.IGNORECASE,
        ).strip()
    if re.search(r"\bul(?:ica)?\.\s", wynik, re.IGNORECASE):
        raise ValueError("Podaj nazwę wydziału bez ulicy")
    if not wynik:
        raise ValueError("Podaj nazwę wydziału")
    return wynik


# Wylicza datę z daty bazowej, dodatniego interwału i jednostki; ogranicza dzień miesiąca, nie zmienia danych.
def oblicz_termin(ostatni: date, interwal: int, jednostka: str) -> date:
    from datetime import timedelta

    if (
        not isinstance(interwal, int)
        or isinstance(interwal, bool)
        or interwal < 1
        or interwal > 12000
    ):
        raise ValueError("Interwał musi być liczbą od 1 do 12000")
    if jednostka == "dzien":
        return ostatni + timedelta(days=interwal)
    if jednostka not in ("miesiac", "rok"):
        raise ValueError("Nieprawidłowa jednostka interwału")
    miesiace = ostatni.year * 12 + ostatni.month - 1 + interwal * (12 if jednostka == "rok" else 1)
    rok, miesiac = divmod(miesiace, 12)
    return date(rok, miesiac + 1, min(ostatni.day, monthrange(rok, miesiac + 1)[1]))


# Ocenia wymagane daty względem dnia w Warszawie; zwraca komentarz lub błąd, bez zapisu.
def sprawdz_daty(status: str, ostatni: date | None, dzis: date) -> str | None:
    if ostatni is None or ostatni > dzis:
        if status == "Nieaktywna":
            return "n/a"
        raise ValueError("Aktywny przyrząd wymaga daty Ostatni niepóźniejszej niż dzisiaj")
    return None


# Zwraca metrologiczną ocenę terminu i dopuszczenie; brak klasy/daty nie jest ważnym sprawdzeniem.
def ocen_status(
    klasa: str,
    status: str,
    stan_techniczny: str,
    ostatni: date | None,
    termin: date | None,
    dzis: date,
    wynik: str | None = None,
) -> dict:
    if klasa not in ("A", "B", "C"):
        return {"metrologiczny": "Brak klasyfikacji", "dopuszczenie": False}
    if klasa == "C":
        metrologiczny = "Nadzór okresowy niewymagany"
    elif ostatni is None or ostatni > dzis or termin is None:
        metrologiczny = "Brak danych do oceny"
    elif wynik == "Negatywny":
        metrologiczny = "Wynik negatywny"
    elif termin < dzis:
        metrologiczny = "Termin przekroczony"
    elif (termin - dzis).days <= 30:
        metrologiczny = "Termin zbliża się"
    else:
        metrologiczny = "W terminie"
    dopuszczenie = (
        status == "Aktywna"
        and stan_techniczny == "Sprawny"
        and metrologiczny in ("W terminie", "Termin zbliża się", "Nadzór okresowy niewymagany")
        and (klasa == "C" or wynik == "Pozytywny")
    )
    return {"metrologiczny": metrologiczny, "dopuszczenie": dopuszczenie}
