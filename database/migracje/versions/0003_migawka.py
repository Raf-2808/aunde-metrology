"""Spójny czas migawki i liczniki QR w publicznej karcie."""

from pathlib import Path
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


# Aktualizuje funkcje publiczne z zamrożonego SQL; czas oceny i zapisu pochodzi z tej samej transakcji.
def upgrade() -> None:
    op.execute(
        sa.text(Path("database/migracje/sql/0003_publiczne.sql").read_text(encoding="utf-8"))
    )


# Przywraca poprzedni kontrakt funkcji, nie usuwa odczytów ani danych przyrządów.
def downgrade() -> None:
    op.execute(
        sa.text(Path("database/migracje/sql/0001_publiczne.sql").read_text(encoding="utf-8"))
    )
