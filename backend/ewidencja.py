"""Zapytania rejestru, filtrowanie i atomowa edycja przyrządów."""

from datetime import date, datetime
from zoneinfo import ZoneInfo
import secrets
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from .modele import (
    Przyrzad,
    TypPrzyrzadu,
    Wydzial,
    Przydzial,
    Harmonogram,
    DaneRR,
    OdczytQR,
    Audyt,
    HistoriaStatusu,
    LinkQR,
    teraz_utc,
)
from .reguly import oblicz_termin, ocen_status, normalizuj_wydzial, sprawdz_daty

STREFA = ZoneInfo("Europe/Warsaw")
POLA = (
    "numer",
    "typ",
    "stan",
    "status",
    "wydzial",
    "klasa",
    "rr",
    "ostatni",
    "interwal",
    "nastepny",
    "jednostka",
    "stan_techniczny",
    "komentarz_dat",
    "metrologiczny",
    "dopuszczenie",
    "ostatni_qr",
    "liczba_qr",
)


# Zwraca datę warszawską, niezależnie od strefy serwera.
def dzis_warszawa() -> date:
    return datetime.now(STREFA).date()


# Tworzy słownik dozwolonych danych i statusu z jednego rekordu zapytania; bez zapisu.
def opisz_przyrzad(
    p: Przyrzad,
    typ: str,
    wydzial: str,
    h: Harmonogram | None,
    liczba: int = 0,
    ostatni_qr: datetime | None = None,
) -> dict:
    ostatni = h.ostatni if h else None
    nastepny = (
        (h.nadpisanie or (oblicz_termin(ostatni, h.interwal, h.jednostka) if ostatni else None))
        if h
        else None
    )
    ocena = ocen_status(
        p.klasa,
        p.status,
        p.stan_techniczny,
        ostatni,
        nastepny,
        dzis_warszawa(),
        h.wynik if h else None,
    )
    if p.stan == "Zwrócona" or p.usunieto_at:
        ocena["dopuszczenie"] = False
    return {
        "id": p.id,
        "numer": p.numer,
        "typ": typ,
        "wydzial": wydzial,
        "stan": p.stan,
        "status": p.status,
        "klasa": p.klasa,
        "stan_techniczny": p.stan_techniczny,
        "komentarz_dat": p.komentarz_dat,
        "wersja": p.wersja,
        "ostatni": ostatni.isoformat() if ostatni else None,
        "nastepny": nastepny.isoformat() if nastepny else None,
        "interwal": h.interwal if h else None,
        "jednostka": h.jednostka if h else "miesiac",
        "proces": h.proces if h else None,
        "wynik": h.wynik if h else None,
        "ostatni_qr": ostatni_qr.isoformat() if ostatni_qr else None,
        "liczba_qr": liczba,
        "usuniety": p.usunieto_at is not None,
        **ocena,
    }


# Pobiera rejestr lub wskazany UUID jednym złączeniem i agregatem QR; R&R tylko dla Administratora, bez zapisu.
def pobierz_rejestr(
    baza: Session, archiwum: bool = False, z_rr: bool = False, identyfikator: str | None = None
) -> list[dict]:
    stat = (
        select(
            OdczytQR.przyrzad_id,
            func.count().label("liczba"),
            func.max(OdczytQR.czas).label("ostatni"),
        )
        .group_by(OdczytQR.przyrzad_id)
        .subquery()
    )
    from sqlalchemy import case

    zapytanie = (
        select(
            Przyrzad,
            TypPrzyrzadu.nazwa,
            Wydzial.nazwa,
            Harmonogram,
            stat.c.liczba,
            stat.c.ostatni,
        )
        .join(TypPrzyrzadu, Przyrzad.typ_id == TypPrzyrzadu.id)
        .join(
            Przydzial,
            (Przydzial.przyrzad_id == Przyrzad.id) & Przydzial.do_at.is_(None),
        )
        .join(Wydzial, Przydzial.wydzial_id == Wydzial.id)
        .outerjoin(
            Harmonogram,
            (Harmonogram.przyrzad_id == Przyrzad.id)
            & (
                Harmonogram.proces
                == case((Przyrzad.klasa == "A", "wzorcowanie"), else_="sprawdzenie")
            ),
        )
        .outerjoin(stat, stat.c.przyrzad_id == Przyrzad.id)
        .where(Przyrzad.usunieto_at.is_not(None) if archiwum else Przyrzad.usunieto_at.is_(None))
    )
    if identyfikator is not None:
        zapytanie = zapytanie.where(Przyrzad.id == identyfikator).execution_options(
            populate_existing=True
        )
    if z_rr:
        zapytanie = zapytanie.add_columns(DaneRR.wartosc).outerjoin(
            DaneRR, DaneRR.przyrzad_id == Przyrzad.id
        )
    dane = []
    for wiersz in baza.execute(zapytanie):
        opis = opisz_przyrzad(*wiersz[:4], wiersz[4] or 0, wiersz[5])
        if z_rr:
            opis["rr"] = wiersz[6] or "---"
        dane.append(opis)
    return dane


# Waliduje kontrakt filtrów; odrzuca nieznane pola i operatory, bez zmiany danych.
def sprawdz_filtry(filtry: dict, z_rr: bool = False) -> None:
    if not isinstance(filtry, dict) or len(filtry) > len(POLA):
        raise ValueError("Nieprawidłowe filtry")
    for pole, filtr in filtry.items():
        if pole not in POLA or (pole == "rr" and not z_rr) or not isinstance(filtr, dict):
            raise ValueError("Nieprawidłowa kolumna filtra")
        if set(filtr) - {"wartosci", "szukaj", "od", "do", "puste"}:
            raise ValueError("Nieprawidłowy operator filtra")
        if "wartosci" in filtr and (
            not isinstance(filtr["wartosci"], list) or len(filtr["wartosci"]) > 5000
        ):
            raise ValueError("Nieprawidłowa lista wartości")


# Zwraca rekordy pasujące do filtrów AND/OR, pustych wartości i zakresów; działa na serwerze.
def filtruj_rejestr(dane: list[dict], filtry: dict, pomin: str | None = None) -> list[dict]:
    wynik = []
    for rekord in dane:
        pasuje = True
        for pole, filtr in filtry.items():
            if pole == pomin:
                continue
            wartosc = rekord.get(pole)
            tekst = "" if wartosc is None else str(wartosc)
            if "wartosci" in filtr and wartosc not in filtr["wartosci"]:
                pasuje = False
            if filtr.get("szukaj") and str(filtr["szukaj"]).casefold() not in tekst.casefold():
                pasuje = False
            if "puste" in filtr and (wartosc is None or wartosc == "") != filtr["puste"]:
                pasuje = False
            for granica, kierunek in (("od", -1), ("do", 1)):
                if filtr.get(granica) not in (None, ""):
                    try:
                        porownywana = float(wartosc) if pole in ("interwal", "liczba_qr") else tekst
                        prog = (
                            float(filtr[granica])
                            if pole in ("interwal", "liczba_qr")
                            else str(filtr[granica])
                        )
                        if (
                            wartosc is None
                            or (kierunek == -1 and porownywana < prog)
                            or (kierunek == 1 and porownywana > prog)
                        ):
                            pasuje = False
                    except (ValueError, TypeError):
                        pasuje = False
        if pasuje:
            wynik.append(rekord)
    return wynik


# Pobiera lub dodaje pozycję słownika przez nazwę; zapisuje ją w bieżącej transakcji.
def zapewnij_slownik(
    baza: Session, model: type[TypPrzyrzadu] | type[Wydzial], nazwa: str
) -> TypPrzyrzadu | Wydzial:
    nazwa = nazwa.strip()
    if not nazwa or len(nazwa) > 150:
        raise ValueError("Nazwa słownika musi mieć od 1 do 150 znaków")
    wynik = baza.scalar(select(model).where(model.nazwa == nazwa))
    if wynik is None:
        wynik = model(nazwa=nazwa)
        baza.add(wynik)
        baza.flush()
    return wynik


# Zapisuje dozwolone zmiany przyrządu pod blokadą rekordu; wymaga zgodnej wersji, zwraca nową wersję.
def zmien_przyrzad(
    baza: Session,
    identyfikator: str,
    wersja: int,
    zmiany: dict,
    uzytkownik_id: str,
    rola: str,
    uzasadnienie: str = "",
) -> Przyrzad:
    p = baza.scalar(select(Przyrzad).where(Przyrzad.id == identyfikator).with_for_update())
    if p is None:
        raise LookupError("Nie znaleziono przyrządu")
    if p.wersja != wersja:
        raise RuntimeError("Rekord zmienił inny użytkownik. Odśwież dane przed zapisem")
    dozwolone = {
        "typ",
        "stan",
        "status",
        "wydzial",
        "klasa",
        "stan_techniczny",
        "ostatni",
        "interwal",
        "jednostka",
    }
    if rola == "Administrator":
        dozwolone |= {"rr", "nastepny", "usuniety"}
    if rola not in ("Editor", "Administrator") or set(zmiany) - dozwolone or not zmiany:
        raise PermissionError("Nie masz uprawnień do zmiany tych pól")
    if p.usunieto_at and set(zmiany) != {"usuniety"}:
        raise ValueError("Przywróć przyrząd przed edycją")
    poprzedni = next(
        r
        for r in pobierz_rejestr(baza, p.usunieto_at is not None, rola == "Administrator")
        if r["id"] == p.id
    )
    przed_zmianami = {pole: poprzedni.get(pole) for pole in zmiany}
    przed = {
        "status": p.status,
        "stan": p.stan,
        "klasa": p.klasa,
        "stan_techniczny": p.stan_techniczny,
    }
    for pole, wartosci in (
        ("status", {"Aktywna", "Nieaktywna"}),
        ("stan", {"Na stanie", "Zwrócona"}),
        ("klasa", {"A", "B", "C"}),
        ("stan_techniczny", {"Sprawny", "Niesprawny", "Nieustalony"}),
    ):
        if pole in zmiany:
            if zmiany[pole] not in wartosci:
                raise ValueError("Niedozwolona wartość pola " + pole)
            if pole == "klasa" and zmiany[pole] != p.klasa and len(uzasadnienie.strip()) < 3:
                raise ValueError("Zmiana klasyfikacji wymaga uzasadnienia")
            setattr(p, pole, zmiany[pole])
    if "typ" in zmiany:
        p.typ_id = zapewnij_slownik(baza, TypPrzyrzadu, str(zmiany["typ"])).id
    if "wydzial" in zmiany:
        wydzial = zapewnij_slownik(baza, Wydzial, normalizuj_wydzial(str(zmiany["wydzial"])))
        stary = baza.scalar(
            select(Przydzial).where(Przydzial.przyrzad_id == p.id, Przydzial.do_at.is_(None))
        )
        if stary is None or stary.wydzial_id != wydzial.id:
            if stary:
                stary.do_at = teraz_utc()
                baza.flush()
            baza.add(Przydzial(przyrzad_id=p.id, wydzial_id=wydzial.id))
    if "rr" in zmiany:
        if zmiany["rr"] not in ("---", "Tak"):
            raise ValueError("Nieprawidłowa wartość R&R")
        rr = baza.get(DaneRR, p.id)
        if rr is None:
            baza.add(DaneRR(przyrzad_id=p.id, wartosc=zmiany["rr"]))
        else:
            rr.wartosc = zmiany["rr"]
    proces = "wzorcowanie" if p.klasa == "A" else "sprawdzenie"
    h = baza.scalar(
        select(Harmonogram).where(Harmonogram.przyrzad_id == p.id, Harmonogram.proces == proces)
    )
    if h is None:
        h = Harmonogram(przyrzad_id=p.id, proces=proces, interwal=12, jednostka="miesiac")
        baza.add(h)
    if h.nadpisanie and set(zmiany) & {"interwal", "jednostka", "ostatni"}:
        raise ValueError("Wycofaj ręczne nadpisanie terminu przed zmianą harmonogramu")
    if "ostatni" in zmiany:
        h.ostatni = date.fromisoformat(zmiany["ostatni"]) if zmiany["ostatni"] else None
        h.wynik = None  # Korekta daty nie jest potwierdzeniem pozytywnego wyniku.
    if "interwal" in zmiany:
        if isinstance(zmiany["interwal"], bool) or not str(zmiany["interwal"]).isdigit():
            raise ValueError("Interwał musi być dodatnią liczbą całkowitą")
        h.interwal = int(zmiany["interwal"])
    if "jednostka" in zmiany:
        h.jednostka = str(zmiany["jednostka"])
    if h.ostatni:
        oblicz_termin(h.ostatni, h.interwal, h.jednostka)
    elif not 1 <= h.interwal <= 12000 or h.jednostka not in ("dzien", "miesiac", "rok"):
        raise ValueError("Nieprawidłowy interwał lub jednostka")
    if zmiany != {"usuniety": True}:
        p.komentarz_dat = sprawdz_daty(p.status, h.ostatni, dzis_warszawa())
    if "nastepny" in zmiany:
        if len(uzasadnienie.strip()) < 3:
            raise ValueError("Zmiana terminu wymaga uzasadnienia")
        h.nadpisanie = date.fromisoformat(zmiany["nastepny"]) if zmiany["nastepny"] else None
        h.uzasadnienie = uzasadnienie
    if "usuniety" in zmiany:
        if not isinstance(zmiany["usuniety"], bool):
            raise ValueError("Nieprawidłowa operacja archiwizacji")
        p.usunieto_at = teraz_utc() if zmiany["usuniety"] else None
    for pole, wartosc in przed.items():
        if getattr(p, pole) != wartosc:
            baza.add(
                HistoriaStatusu(przyrzad_id=p.id, pole=pole, przed=wartosc, po=getattr(p, pole))
            )
    p.wersja += 1
    baza.add(
        Audyt(
            uzytkownik_id=uzytkownik_id,
            rekord_id=p.id,
            operacja="Edycja",
            szczegoly={
                "przed": przed_zmianami,
                "zmiany": zmiany,
                "uzasadnienie": uzasadnienie,
                "wersja": p.wersja,
            },
        )
    )
    baza.flush()
    return p


# Dodaje nieaktywny przyrząd z grupą B, słownikami i trwałym QR; wszystkie operacje należą do jednej transakcji.
def dodaj_przyrzad(
    baza: Session, numer: str, typ: str, wydzial: str, uzytkownik_id: str
) -> Przyrzad:
    if not numer.strip() or len(numer) > 500:
        raise ValueError("Podaj numer przyrządu o długości do 500 znaków")
    if baza.scalar(select(Przyrzad.id).where(Przyrzad.numer == numer.strip())):
        raise ValueError("Numer jest już w rejestrze. Sprawdź także archiwum")
    p = Przyrzad(
        numer=numer.strip(),
        typ_id=zapewnij_slownik(baza, TypPrzyrzadu, typ).id,
        klasa="B",
        status="Nieaktywna",
        stan="Na stanie",
        stan_techniczny="Nieustalony",
        komentarz_dat="n/a",
    )
    baza.add(p)
    baza.flush()
    baza.add_all(
        [
            Przydzial(
                przyrzad_id=p.id,
                wydzial_id=zapewnij_slownik(baza, Wydzial, normalizuj_wydzial(wydzial)).id,
            ),
            Harmonogram(przyrzad_id=p.id, proces="sprawdzenie", interwal=12, jednostka="miesiac"),
            DaneRR(przyrzad_id=p.id),
            LinkQR(przyrzad_id=p.id, token=secrets.token_urlsafe(32)),
            Audyt(
                uzytkownik_id=uzytkownik_id,
                rekord_id=p.id,
                operacja="Dodanie",
                szczegoly={"klasa": "B"},
            ),
        ]
    )
    baza.flush()
    return p
