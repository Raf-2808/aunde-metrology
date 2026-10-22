from datetime import date
import pytest
from backend.reguly import oblicz_termin, normalizuj_wydzial, ocen_status, sprawdz_daty


# Weryfikuje końce miesięcy, rok przestępny i jednostkę bez uproszczenia miesiąca do 30 dni.
@pytest.mark.parametrize(
    "data,interwal,jednostka,oczekiwana",
    [
        (date(2024, 1, 31), 1, "miesiac", date(2024, 2, 29)),
        (date(2023, 1, 31), 1, "miesiac", date(2023, 2, 28)),
        (date(2024, 2, 29), 1, "rok", date(2025, 2, 28)),
        (date(2024, 2, 29), 1, "miesiac", date(2024, 3, 29)),
        (date(2026, 12, 31), 1, "dzien", date(2027, 1, 1)),
        (date(2026, 1, 15), 240, "miesiac", date(2046, 1, 15)),
    ],
)
def test_kalendarza(data, interwal, jednostka, oczekiwana):
    assert oblicz_termin(data, interwal, jednostka) == oczekiwana


# Odrzuca interwały i jednostki poza przyjętym kontraktem.
@pytest.mark.parametrize(
    "interwal,jednostka",
    [(0, "miesiac"), (-1, "rok"), (True, "dzien"), (12001, "rok"), (1, "tydzien")],
)
def test_blednych_interwalow(interwal, jednostka):
    with pytest.raises(ValueError):
        oblicz_termin(date(2026, 1, 1), interwal, jednostka)


# Normalizuje ulicę bez utraty złożonej nazwy wydziału; ponowne wywołanie niczego nie zmienia.
@pytest.mark.parametrize(
    "nazwa,oczekiwana",
    [
        ("Cutter Wersalska", "Cutter"),
        ("Cutter Senatorska", "Cutter"),
        ("Laboratorium Kaczeńcowa", "Laboratorium"),
        ("Laboratorium ul. Kaczeńcowa 12", "Laboratorium"),
        ("Kontrola Jakości", "Kontrola Jakości"),
        (" ESD ", "ESD"),
    ],
)
def test_nazwy_wydzialu(nazwa, oczekiwana):
    assert normalizuj_wydzial(nazwa) == oczekiwana
    assert normalizuj_wydzial(oczekiwana) == oczekiwana


# Brak albo przyszły Ostatni jest dopuszczalny tylko dla nieaktywnych, z komentarzem n/a.
@pytest.mark.parametrize("ostatni", [None, date(2026, 10, 22)])
def test_nieprawidlowych_dat(ostatni):
    assert sprawdz_daty("Nieaktywna", ostatni, date(2026, 10, 21)) == "n/a"
    with pytest.raises(ValueError):
        sprawdz_daty("Aktywna", ostatni, date(2026, 10, 21))


# Ręczna sprawność i aktywność nie znoszą przekroczonego terminu.
def test_blokady_po_terminie():
    wynik = ocen_status(
        "B",
        "Aktywna",
        "Sprawny",
        date(2025, 1, 1),
        date(2026, 1, 1),
        date(2026, 1, 2),
        "Pozytywny",
    )
    assert wynik == {"metrologiczny": "Termin przekroczony", "dopuszczenie": False}


# Termin przypadający dziś jest ważny; brak wyniku nie wymusza dodatkowej blokady.
def test_granicy_dnia_i_wyniku():
    assert ocen_status(
        "B",
        "Aktywna",
        "Sprawny",
        date(2025, 1, 1),
        date(2026, 1, 1),
        date(2026, 1, 1),
        "Pozytywny",
    )["dopuszczenie"]
    assert ocen_status(
        "B", "Aktywna", "Sprawny", date(2025, 1, 1), date(2026, 1, 1), date(2026, 1, 1)
    )["dopuszczenie"]


# Brak klasy nie może stać się zwolnieniem C z obowiązku nadzoru.
def test_braku_klasy():
    assert not ocen_status("", "Aktywna", "Sprawny", None, None, date(2026, 1, 1))["dopuszczenie"]


# Alert terminu pozostaje wymagany także przy niezależnym negatywnym wyniku czynności.
def test_alertu_przy_innej_blokadzie():
    from backend.obsluga import czy_wymaga_alertu

    r = {
        "status": "Aktywna",
        "klasa": "B",
        "nastepny": "2026-01-01",
        "metrologiczny": "Wynik negatywny",
    }
    assert czy_wymaga_alertu(r, date(2026, 1, 2))
    assert not czy_wymaga_alertu({**r, "klasa": "C"}, date(2026, 1, 2))
