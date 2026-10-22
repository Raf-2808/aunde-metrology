"""Unikalność numeru po uzgodnionym połączeniu duplikatu w imporcie."""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


# Zapewnia bazodanową ochronę przed równoległym dodaniem tego samego numeru; źródła pozostają oddzielnie.
def upgrade() -> None:
    op.create_unique_constraint("unikalny_numer_przyrzadu", "przyrzady", ["numer"])


# Usuwa ograniczenie, nie usuwa rekordów ani materiału źródłowego.
def downgrade() -> None:
    op.drop_constraint("unikalny_numer_przyrzadu", "przyrzady", type_="unique")
