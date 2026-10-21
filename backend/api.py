"""Administracyjne API aplikacji. Publiczny serwer używa osobnego modułu i roli bazy."""

from datetime import timedelta, timezone, date
from io import BytesIO
import hashlib
import logging
import os
import secrets
import time
from uuid import uuid4
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError
from fastapi import FastAPI, Depends, Request, Response, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import select, text, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .baza import pobierz_baze
from .modele import (
    Uzytkownik,
    Sesja,
    Przyrzad,
    Harmonogram,
    Sprawdzenie,
    Wzorcowanie,
    LinkQR,
    OdczytQR,
    Audyt,
    teraz_utc,
)
from .ewidencja import (
    pobierz_rejestr,
    sprawdz_filtry,
    filtruj_rejestr,
    zmien_przyrzad,
    dodaj_przyrzad,
    dzis_warszawa,
    POLA,
)

aplikacja = FastAPI(title="AUNDE Metrologia", docs_url=None, redoc_url=None)
haszowanie = PasswordHasher()
CIAS_COOKIE = os.getenv("COOKIE_SECURE", "true").lower() == "true"
PROBY: dict[str, list[float]] = {}
log = logging.getLogger("aunde.api")


class Logowanie(BaseModel):
    login: str = Field(min_length=1, max_length=150)
    haslo: str = Field(min_length=1, max_length=300)


class Zapytanie(BaseModel):
    model_config = ConfigDict(extra="forbid")
    filtry: dict = Field(default_factory=dict)
    strona: int = Field(default=1, ge=1, le=100000)
    rozmiar: int = Field(default=50, ge=1, le=200)
    sortuj: str = "numer"
    malejaco: bool = False
    archiwum: bool = False


class Edycja(BaseModel):
    model_config = ConfigDict(extra="forbid")
    wersja: int = Field(ge=1)
    zmiany: dict
    uzasadnienie: str = Field(default="", max_length=2000)


class NowyPrzyrzad(BaseModel):
    numer: str = Field(min_length=1, max_length=500)
    typ: str = Field(min_length=1, max_length=150)
    wydzial: str = Field(min_length=1, max_length=150)


class Czynnosci(BaseModel):
    wersja: int = Field(ge=1)
    data: date
    wynik: str
    uwagi: str = Field(default="", max_length=2000)
    numer_swiadectwa: str = Field(default="", max_length=250)


class NowyUzytkownik(BaseModel):
    login: str = Field(min_length=3, max_length=150)
    haslo: str = Field(min_length=12, max_length=300)
    rola: str


class ZmianaKonta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rola: str | None = None
    aktywny: bool | None = None
    haslo: str | None = Field(default=None, min_length=12, max_length=300)


# Zamienia błędy walidacji na polski komunikat bez powielania wejścia, tokenów i haseł.
@aplikacja.exception_handler(RequestValidationError)
async def blad_walidacji(zadanie: Request, blad) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": "Nieprawidłowe dane żądania"})


# Tłumaczy spodziewane błędy domenowe na HTTP; nie ujawnia SQL ani konfiguracji.
@aplikacja.exception_handler(ValueError)
async def nieprawidlowa_wartosc(zadanie: Request, blad: ValueError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(blad)})


# Zwraca odmowę nieuprawnionej operacji biznesowej.
@aplikacja.exception_handler(PermissionError)
async def brak_uprawnien(zadanie: Request, blad: PermissionError) -> JSONResponse:
    return JSONResponse(status_code=403, content={"detail": str(blad)})


# Zwraca brak przyrządu zamiast wewnętrznych danych bazy.
@aplikacja.exception_handler(LookupError)
async def brak_rekordu(zadanie: Request, blad: LookupError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(blad)})


# Sygnalizuje konflikt optymistycznej edycji, który wymaga odświeżenia przez użytkownika.
@aplikacja.exception_handler(RuntimeError)
async def konflikt_wersji(zadanie: Request, blad: RuntimeError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(blad)})


# Loguje identyfikator błędu i klasę wyjątku, bez SQL, parametrów, tokenów i treści wejścia.
@aplikacja.exception_handler(Exception)
async def blad_wewnetrzny(zadanie: Request, blad: Exception) -> JSONResponse:
    zdarzenie = str(uuid4())
    log.error(
        "czas=%s modul=api operacja=%s zdarzenie=%s typ=%s",
        teraz_utc().isoformat(),
        zadanie.method,
        zdarzenie,
        type(blad).__name__,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Wystąpił błąd obsługi", "zdarzenie": zdarzenie},
    )


# Odrzuca konflikt ograniczeń integralności bez ujawniania danych zapytania SQL.
@aplikacja.exception_handler(IntegrityError)
async def konflikt_integralnosci(zadanie: Request, blad: IntegrityError) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={"detail": "Dane kolidują z istniejącym wpisem. Odśwież i sprawdź ewidencję"},
    )


# Wyłącza cache odpowiedzi administracyjnych; identyfikator żądania ułatwia diagnostykę.
@aplikacja.middleware("http")
async def zabezpiecz_odpowiedz(zadanie: Request, dalej):
    odpowiedz = await dalej(zadanie)
    odpowiedz.headers["Cache-Control"] = "no-store"
    odpowiedz.headers["X-Request-ID"] = str(uuid4())
    return odpowiedz


# Pobiera aktywną sesję, sprawdza CSRF dla mutacji i zwraca użytkownika; niczego nie modyfikuje.
def zalogowany(zadanie: Request, baza: Session = Depends(pobierz_baze)) -> Uzytkownik:
    token = zadanie.cookies.get("sesja", "")
    sesja = baza.get(Sesja, hashlib.sha256(token.encode()).hexdigest())
    if sesja is None or sesja.wygasa.replace(tzinfo=timezone.utc) <= teraz_utc():
        raise HTTPException(401, "Zaloguj się ponownie")
    u = baza.get(Uzytkownik, sesja.uzytkownik_id)
    if not u or not u.aktywny:
        raise HTTPException(401, "Konto nie jest aktywne")
    if zadanie.method not in ("GET", "HEAD", "OPTIONS"):
        if not secrets.compare_digest(zadanie.headers.get("X-CSRF-Token", ""), sesja.csrf):
            raise HTTPException(403, "Nieprawidłowe zabezpieczenie sesji. Odśwież stronę")
    return u


# Wymaga roli Administrator dla operacji uprzywilejowanej.
def administrator(u: Uzytkownik = Depends(zalogowany)) -> Uzytkownik:
    if u.rola != "Administrator":
        raise HTTPException(403, "Ta operacja wymaga uprawnień administratora")
    return u


# Ogranicza próby logowania i ustanawia bezpieczną sesję; hasła nigdy nie są zwracane.
@aplikacja.post("/api/logowanie")
def zaloguj(
    dane: Logowanie,
    zadanie: Request,
    odpowiedz: Response,
    baza: Session = Depends(pobierz_baze),
) -> dict:
    if zadanie.headers.get("Sec-Fetch-Site") == "cross-site":
        raise HTTPException(403, "Niedozwolone źródło logowania")
    klucz = (zadanie.client.host if zadanie.client else "lokalny") + ":" + dane.login.casefold()
    chwila = time.monotonic()
    proby = [p for p in PROBY.get(klucz, []) if chwila - p < 300]
    if len(proby) >= 10:
        raise HTTPException(429, "Zbyt wiele prób logowania. Spróbuj później")
    PROBY[klucz] = proby + [chwila]
    u = baza.scalar(select(Uzytkownik).where(Uzytkownik.login == dane.login))
    try:
        poprawne = u and u.aktywny and haszowanie.verify(u.skrot_hasla, dane.haslo)
    except (VerifyMismatchError, InvalidHashError):
        poprawne = False
    if not poprawne:
        raise HTTPException(401, "Nieprawidłowy login lub hasło")
    token = secrets.token_urlsafe(32)
    csrf = secrets.token_hex(32)
    baza.add(
        Sesja(
            skrot=hashlib.sha256(token.encode()).hexdigest(),
            uzytkownik_id=u.id,
            csrf=csrf,
            wygasa=teraz_utc() + timedelta(hours=8),
        )
    )
    baza.commit()
    odpowiedz.set_cookie(
        "sesja",
        token,
        httponly=True,
        secure=CIAS_COOKIE,
        samesite="strict",
        max_age=28800,
    )
    return {"login": u.login, "rola": u.rola, "csrf": csrf}


# Zwraca dane konta i CSRF bieżącej sesji po odświeżeniu strony.
@aplikacja.get("/api/sesja")
def pobierz_sesje(
    zadanie: Request,
    u: Uzytkownik = Depends(zalogowany),
    baza: Session = Depends(pobierz_baze),
) -> dict:
    sesja = baza.get(Sesja, hashlib.sha256(zadanie.cookies["sesja"].encode()).hexdigest())
    return {"login": u.login, "rola": u.rola, "csrf": sesja.csrf}


# Unieważnia wyłącznie bieżącą sesję i usuwa cookie.
@aplikacja.post("/api/wylogowanie")
def wyloguj(
    zadanie: Request,
    odpowiedz: Response,
    u: Uzytkownik = Depends(zalogowany),
    baza: Session = Depends(pobierz_baze),
) -> dict:
    sesja = baza.get(Sesja, hashlib.sha256(zadanie.cookies["sesja"].encode()).hexdigest())
    baza.delete(sesja)
    baza.commit()
    odpowiedz.delete_cookie("sesja")
    return {"ok": True}


# Zwraca stronę przefiltrowanej ewidencji z liczbą wyników; R&R tylko dla Administratora.
@aplikacja.post("/api/przyrzady/szukaj")
def pobierz_liste(
    dane: Zapytanie,
    u: Uzytkownik = Depends(zalogowany),
    baza: Session = Depends(pobierz_baze),
) -> dict:
    sprawdz_filtry(dane.filtry, u.rola == "Administrator")
    if dane.sortuj not in POLA or (dane.sortuj == "rr" and u.rola != "Administrator"):
        raise ValueError("Nieprawidłowe sortowanie")
    if dane.archiwum and u.rola != "Administrator":
        raise PermissionError("Archiwum jest dostępne dla administratora")
    rekordy = filtruj_rejestr(
        pobierz_rejestr(baza, dane.archiwum, u.rola == "Administrator"), dane.filtry
    )
    rekordy.sort(
        key=lambda r: (
            r.get(dane.sortuj) is None,
            r.get(dane.sortuj) if r.get(dane.sortuj) is not None else "",
            r["id"],
        ),
        reverse=dane.malejaco,
    )
    start = (dane.strona - 1) * dane.rozmiar
    return {"rekordy": rekordy[start : start + dane.rozmiar], "liczba": len(rekordy)}


# Zwraca podpowiedzi kolumny przy wszystkich filtrach pozostałych kolumn, także poza bieżącą stroną.
@aplikacja.post("/api/wartosci/{pole}")
def pobierz_wartosci(
    pole: str,
    dane: Zapytanie,
    u: Uzytkownik = Depends(zalogowany),
    baza: Session = Depends(pobierz_baze),
) -> dict:
    from collections import Counter

    sprawdz_filtry(dane.filtry, u.rola == "Administrator")
    if pole not in POLA or (pole == "rr" and u.rola != "Administrator"):
        raise PermissionError("Niedostępna kolumna")
    if dane.archiwum and u.rola != "Administrator":
        raise PermissionError("Archiwum jest dostępne dla administratora")
    rekordy = filtruj_rejestr(
        pobierz_rejestr(baza, dane.archiwum, u.rola == "Administrator"),
        dane.filtry,
        pole,
    )
    licznik = Counter(r.get(pole) for r in rekordy)
    return {
        "wartosci": [
            {"wartosc": k, "liczba": v} for k, v in sorted(licznik.items(), key=lambda x: str(x[0]))
        ]
    }


# Zapisuje edycję komórek, audyt i historię w jednej transakcji; konflikt wersji nie nadpisuje danych.
@aplikacja.patch("/api/przyrzady/{identyfikator}")
def zapisz_przyrzad(
    identyfikator: str,
    dane: Edycja,
    u: Uzytkownik = Depends(zalogowany),
    baza: Session = Depends(pobierz_baze),
) -> dict:
    p = zmien_przyrzad(
        baza, identyfikator, dane.wersja, dane.zmiany, u.id, u.rola, dane.uzasadnienie
    )
    baza.commit()
    return {"id": p.id, "wersja": p.wersja}


# Dodaje przyrząd po sprawdzeniu uprawnień; zapisuje słowniki, przydział, QR i audyt atomowo.
@aplikacja.post("/api/przyrzady")
def utworz_przyrzad(
    dane: NowyPrzyrzad,
    u: Uzytkownik = Depends(administrator),
    baza: Session = Depends(pobierz_baze),
) -> dict:
    p = dodaj_przyrzad(baza, dane.numer, dane.typ, dane.wydzial, u.id)
    baza.commit()
    return {"id": p.id}


# Rejestruje rzeczywisty wynik sprawdzenia lub wzorcowania właściwego dla klasy; nie jest odczytem QR.
@aplikacja.post("/api/przyrzady/{identyfikator}/czynnosci")
def zarejestruj_czynnosc(
    identyfikator: str,
    dane: Czynnosci,
    u: Uzytkownik = Depends(zalogowany),
    baza: Session = Depends(pobierz_baze),
) -> dict:
    if u.rola not in ("Editor", "Administrator"):
        raise PermissionError("Nie masz uprawnień do rejestracji czynności")
    if dane.wynik not in ("Pozytywny", "Negatywny") or dane.data > dzis_warszawa():
        raise ValueError("Podaj rzeczywistą datę i wynik czynności")
    p = baza.scalar(select(Przyrzad).where(Przyrzad.id == identyfikator).with_for_update())
    if not p or p.usunieto_at:
        raise LookupError("Nie znaleziono aktywnego przyrządu")
    if p.wersja != dane.wersja:
        raise RuntimeError("Rekord zmienił inny użytkownik")
    if p.klasa == "C":
        raise ValueError(
            "Klasyfikacja C nie ma wymaganego procesu. Najpierw ustal właściwą klasyfikację"
        )
    proces = "wzorcowanie" if p.klasa == "A" else "sprawdzenie"
    h = baza.scalar(
        select(Harmonogram).where(Harmonogram.przyrzad_id == p.id, Harmonogram.proces == proces)
    )
    if h is None:
        h = Harmonogram(przyrzad_id=p.id, proces=proces, interwal=12, jednostka="miesiac")
        baza.add(h)
    if h.ostatni and dane.data < h.ostatni:
        raise ValueError(
            "Nowa czynność nie może być wcześniejsza niż ostatnia. Korektę wykonaj osobno"
        )
    h.ostatni, h.wynik, h.nadpisanie, h.uzasadnienie = dane.data, dane.wynik, None, None
    p.komentarz_dat = None
    model = Wzorcowanie if p.klasa == "A" else Sprawdzenie
    pola = {"numer_swiadectwa": dane.numer_swiadectwa} if p.klasa == "A" else {"uwagi": dane.uwagi}
    if p.klasa == "A" and not dane.numer_swiadectwa.strip():
        raise ValueError("Podaj numer świadectwa lub wewnętrznego raportu wzorcowania")
    baza.add(
        model(
            przyrzad_id=p.id,
            data_wykonania=dane.data,
            wynik=dane.wynik,
            uzytkownik_id=u.id,
            **pola,
        )
    )
    p.wersja += 1
    baza.add(
        Audyt(
            uzytkownik_id=u.id,
            rekord_id=p.id,
            operacja="Czynność metrologiczna",
            szczegoly=dane.model_dump(mode="json"),
        )
    )
    baza.commit()
    return {"wersja": p.wersja}


# Unieważnia poprzedni QR i tworzy nowy tylko na żądanie Administratora; eksport nie rotuje tokenu.
@aplikacja.post("/api/przyrzady/{identyfikator}/qr")
def zmien_token(
    identyfikator: str,
    dane: Edycja,
    u: Uzytkownik = Depends(administrator),
    baza: Session = Depends(pobierz_baze),
) -> dict:
    p = baza.scalar(select(Przyrzad).where(Przyrzad.id == identyfikator).with_for_update())
    if not p:
        raise LookupError("Nie znaleziono przyrządu")
    if p.wersja != dane.wersja:
        raise RuntimeError("Rekord zmienił inny użytkownik")
    for link in baza.scalars(
        select(LinkQR).where(LinkQR.przyrzad_id == p.id, LinkQR.uniewazniono_at.is_(None))
    ):
        link.uniewazniono_at = teraz_utc()
    baza.flush()
    link = LinkQR(przyrzad_id=p.id, token=secrets.token_urlsafe(32))
    baza.add(link)
    p.wersja += 1
    baza.add(
        Audyt(
            uzytkownik_id=u.id,
            rekord_id=p.id,
            operacja="Rotacja QR",
            szczegoly={"wersja": p.wersja},
        )
    )
    baza.commit()
    return {"wersja": p.wersja}


# Udostępnia paginowaną historię QR bez tworzenia odczytu.
@aplikacja.get("/api/przyrzady/{identyfikator}/historia")
def pobierz_historie(
    identyfikator: str,
    strona: int = 1,
    u: Uzytkownik = Depends(zalogowany),
    baza: Session = Depends(pobierz_baze),
) -> dict:
    strona = max(1, min(strona, 100000))
    wpisy = baza.scalars(
        select(OdczytQR)
        .where(OdczytQR.przyrzad_id == identyfikator)
        .order_by(OdczytQR.czas.desc(), OdczytQR.id.desc())
        .offset((strona - 1) * 20)
        .limit(21)
    ).all()
    return {
        "wpisy": [
            {
                "czas": w.czas.isoformat(),
                "status": w.migawka.get("metrologiczny"),
                "dopuszczenie": w.migawka.get("dopuszczenie"),
            }
            for w in wpisy[:20]
        ],
        "dalej": len(wpisy) > 20,
    }


# Eksportuje całą ewidencję albo filtry z aktualnymi obrazami QR; wyłącznie dla Administratora.
@aplikacja.post("/api/eksport")
def eksportuj_excel(
    dane: Zapytanie,
    u: Uzytkownik = Depends(administrator),
    baza: Session = Depends(pobierz_baze),
) -> StreamingResponse:
    from .eksport import zbuduj_excel

    sprawdz_filtry(dane.filtry, True)
    rekordy = filtruj_rejestr(pobierz_rejestr(baza, dane.archiwum, True), dane.filtry)
    linki = {
        l.przyrzad_id: l.token
        for l in baza.scalars(select(LinkQR).where(LinkQR.uniewazniono_at.is_(None)))
    }
    wynik = zbuduj_excel(rekordy, linki, os.environ["PUBLIC_BASE_URL"])
    return StreamingResponse(
        BytesIO(wynik),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="aunde-metrologia.xlsx"',
            "Cache-Control": "no-store",
        },
    )


# Tworzy konto z hasłem Argon2id; zwraca wyłącznie identyfikator, loguje operację bez hasła.
@aplikacja.post("/api/uzytkownicy")
def dodaj_uzytkownika(
    dane: NowyUzytkownik,
    u: Uzytkownik = Depends(administrator),
    baza: Session = Depends(pobierz_baze),
) -> dict:
    if dane.rola not in ("Viewer", "Editor", "Administrator"):
        raise ValueError("Nieprawidłowa rola")
    if baza.scalar(select(Uzytkownik.id).where(Uzytkownik.login == dane.login)):
        raise ValueError("Taki login już istnieje")
    nowy = Uzytkownik(login=dane.login, skrot_hasla=haszowanie.hash(dane.haslo), rola=dane.rola)
    baza.add(nowy)
    baza.flush()
    baza.add(
        Audyt(
            uzytkownik_id=u.id,
            rekord_id=nowy.id,
            operacja="Dodanie konta",
            szczegoly={"login": nowy.login, "rola": nowy.rola},
        )
    )
    baza.commit()
    return {"id": nowy.id}


# Udostępnia listę kont bez skrótów haseł i sesji, wyłącznie Administratorowi.
@aplikacja.get("/api/uzytkownicy")
def pobierz_konta(
    u: Uzytkownik = Depends(administrator), baza: Session = Depends(pobierz_baze)
) -> list[dict]:
    return [
        {"id": k.id, "login": k.login, "rola": k.rola, "aktywny": k.aktywny}
        for k in baza.scalars(select(Uzytkownik).order_by(Uzytkownik.login))
    ]


# Zmienia rolę, aktywność lub hasło i unieważnia sesje; blokuje usunięcie ostatniego aktywnego Administratora.
@aplikacja.patch("/api/uzytkownicy/{identyfikator}")
def zmien_konto(
    identyfikator: str,
    dane: ZmianaKonta,
    u: Uzytkownik = Depends(administrator),
    baza: Session = Depends(pobierz_baze),
) -> dict:
    konta = baza.scalars(select(Uzytkownik).order_by(Uzytkownik.id).with_for_update()).all()
    konto = next((k for k in konta if k.id == identyfikator), None)
    if konto is None:
        raise LookupError("Nie znaleziono konta")
    if dane.rola is not None and dane.rola not in ("Viewer", "Editor", "Administrator"):
        raise ValueError("Nieprawidłowa rola")
    poprzednie = {"rola": konto.rola, "aktywny": konto.aktywny}
    if dane.rola is not None:
        konto.rola = dane.rola
    if dane.aktywny is not None:
        konto.aktywny = dane.aktywny
    if not any(k.aktywny and k.rola == "Administrator" for k in konta):
        raise ValueError("Musi pozostać przynajmniej jeden aktywny Administrator")
    if dane.haslo is not None:
        konto.skrot_hasla = haszowanie.hash(dane.haslo)
    baza.execute(delete(Sesja).where(Sesja.uzytkownik_id == konto.id))
    baza.add(
        Audyt(
            uzytkownik_id=u.id,
            rekord_id=konto.id,
            operacja="Zmiana konta",
            szczegoly={
                "przed": poprzednie,
                "rola": konto.rola,
                "aktywny": konto.aktywny,
                "zmiana_hasla": dane.haslo is not None,
            },
        )
    )
    baza.commit()
    return {"id": konto.id}


# Sprawdza połączenie bazy do healthcheck kontenera, bez ujawnienia konfiguracji.
@aplikacja.get("/health")
def sprawdz_zdrowie(baza: Session = Depends(pobierz_baze)) -> dict:
    baza.execute(text("SELECT 1"))
    return {"ok": True}
