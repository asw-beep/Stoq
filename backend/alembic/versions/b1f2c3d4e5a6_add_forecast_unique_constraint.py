"""add unique constraint on forecasts (stock, model, dates)

Phase 2: a model run for a given day produces one row per target date; the
service replaces a day's rows on re-run. This constraint enforces that grain.

Revision ID: b1f2c3d4e5a6
Revises: 46e23ed0b9b3
Create Date: 2026-06-14 00:00:00.000000
"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b1f2c3d4e5a6'
down_revision: str | None = '46e23ed0b9b3'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CONSTRAINT = 'uq_forecast_stock_model_dates'


def upgrade() -> None:
    op.create_unique_constraint(
        _CONSTRAINT,
        'forecasts',
        ['stock_id', 'model', 'forecast_date', 'target_date'],
    )


def downgrade() -> None:
    op.drop_constraint(_CONSTRAINT, 'forecasts', type_='unique')
