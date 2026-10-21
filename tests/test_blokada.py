"""Ręczna blokada jest niezależna od aktywności i wyniku, termin ma pierwszeństwo."""

from datetime import date, timedelta
import pytest
from sqlalchemy import select
from backend.reguly import ocen_status
from backend.ewidencja import dodaj_przyrzad, zmien_przyrzad, pobierz_rejestr, dzis_warszawa
from backend.modele import Harmonogram, Audyt, HistoriaStatusu


# Sprawdza granicę terminu dla A/B i brak automatycznego terminu dla C niezależnie od innych pól.
@pytest.mark.parametrize("klasa", ["A", "B", "C"])
@pytest.mark.parametrize("przesuniecie", [-1, 0, 1])
def test_pierwszenstwa_terminu(klasa: str, przesuniecie: int) -> None:
    dzis = date(2026, 10, 21)
    ocena = ocen_status(
        klasa,
        "Nieaktywna",
        "Nieustalony",
        date(2025, 1, 1),
        dzis + timedelta(days=przesuniecie),
        dzis,
        "Negatywny",
        True,
    )
    assert ocena["dopuszczenie"] == (klasa == "C" or przesuniecie >= 0)
    assert not ocen_status(
        klasa, "Aktywna", "Sprawny", date(2025, 1, 1), dzis, dzis, "Pozytywny", False
    )["dopuszczenie"]


# Nieaktywne n/a można ręcznie odblokować; zwrot i nieznany stan techniczny nie wymuszają blokady.
def test_edycji_blokady_i_audytu(baza) -> None:
    p = dodaj_przyrzad(baza, "BLOKADA-1", "Miara", "ESD", None)
    baza.commit()
    assert not pobierz_rejestr(baza)[0]["dopuszczenie"]
    zmien_przyrzad(baza, p.id, 1, {"odblokowany": True, "stan": "Zwrócona"}, None, "Editor")
    baza.commit()
    assert pobierz_rejestr(baza)[0]["dopuszczenie"]
    assert pobierz_rejestr(baza)[0]["komentarz_dat"] == "n/a"
    assert (
        baza.scalar(select(HistoriaStatusu).where(HistoriaStatusu.pole == "odblokowany"))
        is not None
    )
    audyt = baza.scalars(select(Audyt).where(Audyt.operacja == "Edycja")).one()
    assert audyt.szczegoly["zmiany"]["odblokowany"] is True
    assert audyt.szczegoly["przed"]["odblokowany"] is False
    with pytest.raises(PermissionError):
        zmien_przyrzad(baza, p.id, 2, {"odblokowany": False}, None, "Viewer")
    zmien_przyrzad(baza, p.id, 2, {"odblokowany": False}, None, "Administrator")
    baza.commit()
    assert not pobierz_rejestr(baza)[0]["dopuszczenie"]


# Niesprawny blokuje automatycznie; Sprawny usuwa tylko tę przyczynę, bez znoszenia terminu lub blokady ręcznej.
def test_zmiany_niesprawny_na_sprawny(baza) -> None:
    p = dodaj_przyrzad(baza, "BLOKADA-3", "Miara", "ESD", None)
    p.odblokowany = True
    baza.commit()
    zmien_przyrzad(baza, p.id, 1, {"stan_techniczny": "Niesprawny"}, None, "Editor")
    baza.commit()
    assert not pobierz_rejestr(baza)[0]["dopuszczenie"]
    with pytest.raises(ValueError, match="niesprawny"):
        zmien_przyrzad(baza, p.id, 2, {"odblokowany": True}, None, "Administrator")
    baza.rollback()
    zmien_przyrzad(baza, p.id, 2, {"stan_techniczny": "Sprawny"}, None, "Editor")
    baza.commit()
    assert pobierz_rejestr(baza)[0]["dopuszczenie"]
    zmien_przyrzad(
        baza, p.id, 3, {"odblokowany": False, "stan_techniczny": "Niesprawny"}, None, "Editor"
    )
    baza.commit()
    zmien_przyrzad(baza, p.id, 4, {"stan_techniczny": "Sprawny"}, None, "Editor")
    baza.commit()
    assert not pobierz_rejestr(baza)[0]["dopuszczenie"]


# Termin blokuje także ręcznie odblokowany rekord; zarejestrowanie aktualnej czynności przywraca ustawienie.
def test_blokady_po_terminie_i_przywrocenia(baza) -> None:
    p = dodaj_przyrzad(baza, "BLOKADA-2", "Miara", "ESD", None)
    baza.flush()
    h = baza.scalar(select(Harmonogram).where(Harmonogram.przyrzad_id == p.id))
    h.ostatni = dzis_warszawa() - timedelta(days=2)
    h.interwal, h.jednostka = 1, "dzien"
    p.odblokowany = True
    baza.commit()
    assert not pobierz_rejestr(baza)[0]["dopuszczenie"]
    assert pobierz_rejestr(baza)[0]["odblokowany"]
    with pytest.raises(ValueError, match="Termin został przekroczony"):
        zmien_przyrzad(baza, p.id, 1, {"odblokowany": True}, None, "Administrator")
    baza.rollback()
    h = baza.scalar(select(Harmonogram).where(Harmonogram.przyrzad_id == p.id))
    h.ostatni = dzis_warszawa()
    baza.commit()
    assert pobierz_rejestr(baza)[0]["dopuszczenie"]
