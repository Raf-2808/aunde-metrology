"""Migracje uruchamiane wyłącznie z rolą właściciela schematu."""

import os
from alembic import context
from sqlalchemy import create_engine
from backend.modele import Baza


# Wykonuje migracje online w transakcji i nie ujawnia URL bazy w logach.
def wykonaj_migracje() -> None:
    silnik = create_engine(os.environ["DATABASE_URL"])
    with silnik.connect() as polaczenie:
        context.configure(connection=polaczenie, target_metadata=Baza.metadata)
        with context.begin_transaction():
            context.run_migrations()


wykonaj_migracje()
