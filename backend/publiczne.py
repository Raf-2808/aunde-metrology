"""Publiczna karta QR. Połączenie DB ma tylko prawo wykonania ograniczonych funkcji."""

from datetime import date, datetime
import json
from uuid import UUID, uuid4
import logging
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session
from .baza import pobierz_baze
from .ewidencja import STREFA
from .reguly import ocen_status, oblicz_termin
from .modele import teraz_utc

aplikacja = FastAPI(title="Karta przyrządu", docs_url=None, redoc_url=None, openapi_url=None)


class Otwarcie(BaseModel):
    zdarzenie: UUID


# Ustawia brak cache i ogranicza dane diagnostyczne; publiczne odpowiedzi nie ujawniają wyjątków bazy.
@aplikacja.middleware("http")
async def zabezpiecz_odpowiedz(zadanie: Request, dalej):
    try:
        wynik = await dalej(zadanie)
    except Exception as blad:
        zdarzenie = str(uuid4())
        logging.getLogger("aunde.publiczne").error(
            "czas=%s modul=publiczne operacja=%s zdarzenie=%s typ=%s",
            teraz_utc().isoformat(),
            zadanie.method,
            zdarzenie,
            type(blad).__name__,
        )
        wynik = JSONResponse(
            status_code=503,
            content={
                "detail": "Nie udało się zapisać odczytu. Spróbuj ponownie",
                "zdarzenie": zdarzenie,
            },
        )
    wynik.headers["Cache-Control"] = "no-store"
    wynik.headers["X-Robots-Tag"] = "noindex, nofollow"
    wynik.headers["Referrer-Policy"] = "no-referrer"
    return wynik


# Automatycznie zapisuje jedno otwarcie z idempotencją; migawka statusu powstaje pod blokadą wspólnego rekordu.
@aplikacja.post("/public/otwarcie/{token}")
def zarejestruj_odczyt(
    token: str, dane: Otwarcie, zadanie: Request, baza: Session = Depends(pobierz_baze)
) -> dict:
    if len(token) != 43:
        raise HTTPException(404, "Karta jest niedostępna")
    if zadanie.headers.get("Sec-Fetch-Site") == "cross-site" or any(
        "prefetch" in zadanie.headers.get(nazwa, "").lower() for nazwa in ("Purpose", "Sec-Purpose")
    ):
        raise HTTPException(403, "Podgląd linku nie jest odczytem QR")
    surowe = baza.scalar(text("SELECT public.przygotuj_karte(:token)"), {"token": token})
    if not surowe:
        raise HTTPException(404, "Karta jest niedostępna")
    # Lista dozwolonych pól pochodzi z funkcji SQL, nigdy z serializacji całego ORM.
    ostatni = date.fromisoformat(surowe["ostatni"]) if surowe.get("ostatni") else None
    termin = (
        date.fromisoformat(surowe["nadpisanie"])
        if surowe.get("nadpisanie")
        else oblicz_termin(ostatni, surowe["interwal"], surowe["jednostka"])
        if ostatni
        else None
    )
    surowe["nastepny"] = termin.isoformat() if termin else None
    surowe.update(
        ocen_status(
            surowe["klasa"],
            surowe["status"],
            surowe["stan_techniczny"],
            ostatni,
            termin,
            datetime.fromisoformat(surowe["czas_oceny"]).astimezone(STREFA).date(),
            surowe.get("wynik"),
            surowe.pop("odblokowany", False),
        )
    )
    surowe.pop("nadpisanie", None)
    wynik = baza.scalar(
        text("SELECT public.zapisz_odczyt(:token, :zdarzenie, CAST(:migawka AS jsonb))"),
        {
            "token": token,
            "zdarzenie": str(dane.zdarzenie),
            "migawka": json.dumps(surowe, ensure_ascii=False),
        },
    )
    if not wynik:
        raise HTTPException(409, "Identyfikator odczytu został już użyty. Otwórz kartę ponownie")
    baza.commit()
    return wynik


# Pobiera wyłącznie historię odczytów aktywnego tokenu; nie generuje kolejnego odczytu.
@aplikacja.get("/public/historia/{token}")
def pobierz_historie(token: str, strona: int = 1, baza: Session = Depends(pobierz_baze)) -> dict:
    if len(token) != 43:
        raise HTTPException(404, "Karta jest niedostępna")
    wynik = baza.scalar(
        text("SELECT public.historia_karty(:token, :strona)"),
        {"token": token, "strona": max(1, min(strona, 100000))},
    )
    if wynik is None:
        raise HTTPException(404, "Karta jest niedostępna")
    return wynik


# Sprawdza żywotność procesu bez dostępu do tabel administracyjnych.
@aplikacja.get("/health")
def sprawdz_zdrowie() -> dict:
    return {"ok": True}
