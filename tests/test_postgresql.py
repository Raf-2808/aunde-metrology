"""Testy rzeczywistego PostgreSQL, oddzielne od testów SQLite. Wymagają TEST_DATABASE_URL."""

import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import json
import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import DBAPIError
from backend.ewidencja import dodaj_przyrzad, zmien_przyrzad
from backend.modele import LinkQR, Przyrzad


# Karta publiczna stosuje tę samą blokadę ręczną i techniczną co rejestr, bez ujawniania ustawienia i R&R.
def test_spojnosci_blokady_publicznej(polaczenia_pg):
    from fastapi.testclient import TestClient
    from backend.publiczne import aplikacja
    from backend.baza import pobierz_baze
    from backend.ewidencja import pobierz_rejestr

    sesje, silnik_publiczny = polaczenia_pg
    publiczne_sesje = sessionmaker(silnik_publiczny)
    with sesje.begin() as baza:
        p = dodaj_przyrzad(baza, "TEST-BLOKADA-" + str(uuid4()), "Miara", "ESD", None)
        identyfikator = p.id
        token = baza.scalar(select(LinkQR.token).where(LinkQR.przyrzad_id == p.id))

    # Udostępnia tylko ograniczoną rolę PostgreSQL dla wywołania testowanego publicznego API.
    def publiczna_baza():
        with publiczne_sesje() as baza:
            yield baza

    aplikacja.dependency_overrides[pobierz_baze] = publiczna_baza
    try:
        with TestClient(aplikacja) as klient:
            for wersja, zmiany, oczekiwany in (
                (1, {"odblokowany": True}, True),
                (2, {"stan_techniczny": "Niesprawny"}, False),
                (3, {"stan_techniczny": "Sprawny"}, True),
                (4, {"odblokowany": False}, False),
            ):
                with sesje.begin() as baza:
                    zmien_przyrzad(baza, identyfikator, wersja, zmiany, None, "Editor")
                    assert (
                        pobierz_rejestr(baza, identyfikator=identyfikator)[0]["dopuszczenie"]
                        is oczekiwany
                    )
                wynik = klient.post("/public/otwarcie/" + token, json={"zdarzenie": str(uuid4())})
                assert wynik.status_code == 200
                karta = wynik.json()["przyrzad"]
                assert karta["dopuszczenie"] is oczekiwany
                assert "odblokowany" not in karta and "rr" not in karta
    finally:
        aplikacja.dependency_overrides.clear()


pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="Wymagany rzeczywisty PostgreSQL"
)


# Udostępnia połączenia z dedykowaną bazą PostgreSQL, bez użycia baz produkcyjnych.
@pytest.fixture
def polaczenia_pg():
    adres = os.environ["TEST_DATABASE_URL"]
    if "test" not in adres.rsplit("/", 1)[-1]:
        pytest.fail("Nazwa bazy testowej musi zawierać test")
    silnik = create_engine(adres)
    publiczny = create_engine(os.environ["TEST_PUBLIC_DATABASE_URL"])
    yield sessionmaker(silnik, expire_on_commit=False), publiczny
    silnik.dispose()
    publiczny.dispose()


# Rzeczywista blokada rekordu dopuszcza jeden zapis dwóch równoległych edycji o tej samej wersji.
def test_rownoczesnych_edycji_postgresql(polaczenia_pg):
    sesje, _ = polaczenia_pg
    with sesje.begin() as baza:
        p = dodaj_przyrzad(baza, "TEST-" + str(uuid4()), "Miara", "Cutter Wersalska", None)
        identyfikator = p.id

    # Próbuje atomowej zmiany z wersją 1 w osobnym połączeniu i zwraca wynik konfliktu.
    def edytuj(stan: str) -> str:
        try:
            with sesje.begin() as baza:
                zmien_przyrzad(baza, identyfikator, 1, {"stan": stan}, None, "Editor")
            return "zapisano"
        except RuntimeError:
            return "konflikt"

    with ThreadPoolExecutor(max_workers=2) as wykonawca:
        wyniki = list(wykonawca.map(edytuj, ["Zwrócona", "Na stanie"]))
    assert sorted(wyniki) == ["konflikt", "zapisano"]
    with sesje() as baza:
        assert baza.get(Przyrzad, identyfikator).wersja == 2


# Ograniczona rola publiczna nie czyta R&R i nie zmienia ewidencji; funkcja zapisuje idempotentny odczyt.
def test_ograniczen_i_odczytu_postgresql(polaczenia_pg):
    sesje, publiczny = polaczenia_pg
    with sesje.begin() as baza:
        p = dodaj_przyrzad(baza, "TEST-" + str(uuid4()), "Miara", "Magazyn Senatorska", None)
        token = baza.scalar(select(LinkQR.token).where(LinkQR.przyrzad_id == p.id))
    for sql in (
        "SELECT * FROM public.dane_rr",
        "UPDATE public.przyrzady SET status='Aktywna'",
        "DELETE FROM public.odczyty_qr",
    ):
        with pytest.raises(DBAPIError):
            with publiczny.begin() as c:
                c.execute(text(sql))
    zdarzenie = str(uuid4())
    with publiczny.begin() as c:
        karta = c.scalar(text("SELECT public.przygotuj_karte(:token)"), {"token": token})
        assert "rr" not in karta and "R&R" not in karta
        assert karta["wydzial"] == "Magazyn"
        karta.update(
            {
                "rr": "SEKRET",
                "metrologiczny": "Brak danych do oceny",
                "dopuszczenie": False,
            }
        )
        parametry = {"token": token, "id": zdarzenie, "migawka": json.dumps(karta)}
        pierwszy = c.scalar(
            text("SELECT public.zapisz_odczyt(:token,:id,CAST(:migawka AS jsonb))"),
            parametry,
        )
        drugi = c.scalar(
            text("SELECT public.zapisz_odczyt(:token,:id,CAST(:migawka AS jsonb))"),
            parametry,
        )
        assert pierwszy == drugi
        assert pierwszy["czas"] == karta["czas_oceny"]
        assert "rr" not in pierwszy["przyrzad"]
    with publiczny.begin() as c:
        historia = c.scalar(text("SELECT public.historia_karty(:token,1)"), {"token": token})
        assert len(historia["wpisy"]) == 1
        assert "rr" not in json.dumps(historia)


# Unieważnienie linku blokuje starą kartę i nie niszczy istniejącej historii odczytów.
def test_uniewaznienia_postgresql(polaczenia_pg):
    from backend.modele import teraz_utc

    sesje, publiczny = polaczenia_pg
    with sesje.begin() as baza:
        p = dodaj_przyrzad(baza, "TEST-" + str(uuid4()), "Waga", "Laboratorium", None)
        link = baza.scalar(select(LinkQR).where(LinkQR.przyrzad_id == p.id))
        token = link.token
        link.uniewazniono_at = teraz_utc()
    with publiczny.begin() as c:
        assert c.scalar(text("SELECT public.przygotuj_karte(:token)"), {"token": token}) is None
        assert c.scalar(text("SELECT public.historia_karty(:token,1)"), {"token": token}) is None


# Sprawdza kolejkę i brak ponownej wysyłki alertu, zastępując SMTP atrapą bez połączenia sieciowego.
def test_powiadomien_bez_wysylki_zewnetrznej(polaczenia_pg, monkeypatch):
    from datetime import timedelta
    from unittest.mock import MagicMock
    from backend import obsluga
    from backend.ewidencja import dzis_warszawa

    sesje, _ = polaczenia_pg
    with sesje.begin() as baza:
        p = dodaj_przyrzad(baza, "TEST-EMAIL-" + str(uuid4()), "Miara", "ESD", None)
        zmien_przyrzad(
            baza,
            p.id,
            1,
            {
                "status": "Aktywna",
                "ostatni": (dzis_warszawa() - timedelta(days=400)).isoformat(),
                "interwal": 1,
            },
            None,
            "Editor",
        )
    monkeypatch.setattr(obsluga, "SesjaBazy", sesje)
    monkeypatch.setenv("EMAIL_ENABLED", "true")
    monkeypatch.setenv("SMTP_HOST", "smtp.test.invalid")
    monkeypatch.setenv("SMTP_FROM", "metrologia@test.invalid")
    smtp = MagicMock()
    monkeypatch.setattr(obsluga.smtplib, "SMTP", smtp)
    obsluga.obsluz_powiadomienia()
    pierwsze = smtp.return_value.__enter__.return_value.send_message.call_count
    assert pierwsze >= 1
    wiadomosc = smtp.return_value.__enter__.return_value.send_message.call_args.args[0]
    assert wiadomosc["To"] == "jakosc@aunde.pl"
    assert "\u2014" not in wiadomosc.get_content()
    obsluga.obsluz_powiadomienia()
    assert smtp.return_value.__enter__.return_value.send_message.call_count == pierwsze
