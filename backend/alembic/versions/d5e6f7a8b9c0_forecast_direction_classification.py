"""Switch forecasts to directional classification

Adds direction (smallint) and probability (numeric) columns for the new
XGBoost classifier output. Makes predicted_price nullable so old regression
rows are preserved and the column is no longer required for new inserts.

Revision ID: d5e6f7a8b9c0
Revises: c3d4e5f6a7b8
Create Date: 2026-06-20 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d5e6f7a8b9c0"
down_revision: str | None = "c3d4e5f6a7b8"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("forecasts", sa.Column("direction", sa.SmallInteger(), nullable=True))
    op.add_column("forecasts", sa.Column("probability", sa.Numeric(6, 4), nullable=True))
    op.alter_column("forecasts", "predicted_price", existing_type=sa.Numeric(18, 4), nullable=True)


def downgrade() -> None:
    op.alter_column("forecasts", "predicted_price", existing_type=sa.Numeric(18, 4), nullable=False)
    op.drop_column("forecasts", "probability")
    op.drop_column("forecasts", "direction")
