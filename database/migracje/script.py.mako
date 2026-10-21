"""${message}"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = None
depends_on = None

# Wprowadza zatwierdzoną zmianę schematu w transakcji migracyjnej.
def upgrade() -> None:
    ${upgrades if upgrades else "pass"}

# Wycofuje zmianę schematu; przed wykonaniem wymagany jest backup danych.
def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
