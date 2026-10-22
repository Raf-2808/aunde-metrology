"""Ręczna blokada, początkowo zgodna z aktywnością, z pierwszeństwem terminu."""

from pathlib import Path
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


# Dodaje ustawienie blokady, inicjalizuje istniejące przyrządy i audytuje jednorazową zmianę.
def upgrade() -> None:
    op.add_column(
        "przyrzady",
        sa.Column("odblokowany", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute("UPDATE public.przyrzady SET odblokowany=(status='Aktywna'), wersja=wersja+1")
    op.execute("""
        INSERT INTO public.audyt(id,rekord_id,operacja,szczegoly,czas)
        SELECT gen_random_uuid()::text,id,'Inicjalizacja blokady',
          json_build_object('odblokowany',odblokowany,'regula','Aktywna: odblokowany, pozostale: zablokowany; termin ma pierwszenstwo'),
          transaction_timestamp() FROM public.przyrzady
    """)
    op.execute(
        sa.text(Path("database/migracje/sql/0004_publiczne.sql").read_text(encoding="utf-8"))
    )


# Przywraca poprzedni kontrakt karty i usuwa ustawienie ręczne; wcześniejszy audyt pozostaje.
def downgrade() -> None:
    op.execute(
        sa.text(Path("database/migracje/sql/0003_publiczne.sql").read_text(encoding="utf-8"))
    )
    op.drop_column("przyrzady", "odblokowany")
