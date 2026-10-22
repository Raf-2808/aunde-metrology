"""Konfiguracja połączenia; migracje mają oddzielną tożsamość od aplikacji."""

import os
from collections.abc import Iterator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

ADRES_BAZY = os.environ["DATABASE_URL"]
silnik = create_engine(ADRES_BAZY, pool_pre_ping=True, hide_parameters=True)
SesjaBazy = sessionmaker(silnik, expire_on_commit=False)


# Udostępnia transakcyjną sesję na czas żądania; zamyka ją także przy błędzie.
def pobierz_baze() -> Iterator[Session]:
    with SesjaBazy() as baza:
        yield baza
