import pytest
from backend.ewidencja import (
    dodaj_przyrzad,
    zmien_przyrzad,
    pobierz_rejestr,
    filtruj_rejestr,
    sprawdz_filtry,
)
from backend.modele import LinkQR, Audyt, Przydzial
from sqlalchemy import select


# Dodaje przyrząd z B i wydziałem bez ulicy; zmiana przydziału nie zmienia trwałego tokenu QR.
def test_dodania_i_przydzialu(baza):
    p = dodaj_przyrzad(baza, "T001", "Suwmiarka", "Laboratorium Wersalska", None)
    baza.commit()
    assert p.klasa == "B"
    token = baza.scalar(select(LinkQR.token))
    zmien_przyrzad(baza, p.id, 1, {"wydzial": "Cutter Senatorska"}, None, "Editor")
    baza.commit()
    dane = pobierz_rejestr(baza)
    assert dane[0]["wydzial"] == "Cutter"
    assert dane[0]["komentarz_dat"] == "n/a"
    assert baza.scalar(select(LinkQR.token)) == token
    assert len(baza.scalars(select(Przydzial)).all()) == 2


# Odrzuca nieaktualną wersję i nie zmienia danych podczas konfliktu.
def test_konfliktu_wersji(baza):
    p = dodaj_przyrzad(baza, "T002", "Miara zwijana", "Magazyn", None)
    baza.commit()
    zmien_przyrzad(baza, p.id, 1, {"stan": "Zwrócona"}, None, "Editor")
    baza.commit()
    with pytest.raises(RuntimeError):
        zmien_przyrzad(baza, p.id, 1, {"stan": "Na stanie"}, None, "Editor")
    assert p.stan == "Zwrócona"


# Viewer nie edytuje, Editor nie usuwa i nie otrzymuje R&R z zapytania rejestru.
def test_uprawnien(baza):
    p = dodaj_przyrzad(baza, "T003", "Miara", "ESD", None)
    baza.commit()
    for rola, pole in (("Viewer", "stan"), ("Editor", "usuniety"), ("Editor", "rr")):
        with pytest.raises(PermissionError):
            zmien_przyrzad(baza, p.id, 1, {pole: "Tak"}, None, rola)
    assert "rr" not in pobierz_rejestr(baza)[0]
    assert "rr" in pobierz_rejestr(baza, z_rr=True)[0]


# Soft delete ukrywa rekord aktywny i przywrócenie zachowuje UUID oraz historię.
def test_archiwum(baza):
    p = dodaj_przyrzad(baza, "T004", "Miara", "ESD", None)
    baza.commit()
    zmien_przyrzad(baza, p.id, 1, {"usuniety": True}, None, "Administrator")
    baza.commit()
    assert pobierz_rejestr(baza) == []
    assert pobierz_rejestr(baza, archiwum=True)[0]["id"] == p.id
    zmien_przyrzad(baza, p.id, 2, {"usuniety": False}, None, "Administrator")
    baza.commit()
    assert pobierz_rejestr(baza)[0]["id"] == p.id
    assert len(baza.scalars(select(Audyt)).all()) == 3


# Filtrowanie łączy kolumny przez AND i wartości jednej kolumny przez OR; obsługuje puste i daty.
def test_filtrow_i_podpowiedzi():
    dane = [
        {"typ": "Miara", "wydzial": "ESD", "ostatni": None, "interwal": 12},
        {"typ": "Miara", "wydzial": "Cutter", "ostatni": "2026-01-01", "interwal": 6},
        {"typ": "Waga", "wydzial": "ESD", "ostatni": "2026-02-01", "interwal": 24},
    ]
    filtry = {"typ": {"wartosci": ["Miara"]}, "wydzial": {"wartosci": ["ESD"]}}
    assert len(filtruj_rejestr(dane, filtry)) == 1
    assert len(filtruj_rejestr(dane, filtry, "typ")) == 2
    assert len(filtruj_rejestr(dane, {"ostatni": {"puste": True}})) == 1
    assert len(filtruj_rejestr(dane, {"interwal": {"od": "12", "do": "24"}})) == 2
    assert len(filtruj_rejestr(dane, {"ostatni": {"od": "2026-01-15"}})) == 1
    assert filtruj_rejestr(dane, {"typ": {"wartosci": []}}) == []
    with pytest.raises(ValueError):
        sprawdz_filtry({"rr": {"wartosci": ["Tak"]}})
