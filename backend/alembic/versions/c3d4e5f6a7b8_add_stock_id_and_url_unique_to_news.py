"""add stock_id FK and url unique constraint to news_articles

Phase 4: links each article to the stock it was fetched for, and prevents
duplicate articles being stored from repeated Finnhub fetches.

Revision ID: c3d4e5f6a7b8
Revises: b1f2c3d4e5a6
Create Date: 2026-06-15 00:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'c3d4e5f6a7b8'
down_revision: str | None = 'b1f2c3d4e5a6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'news_articles',
        sa.Column('stock_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'fk_news_articles_stock_id',
        'news_articles',
        'stocks',
        ['stock_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_index('ix_news_articles_stock_id', 'news_articles', ['stock_id'], unique=False)
    op.create_unique_constraint('uq_news_url', 'news_articles', ['url'])


def downgrade() -> None:
    op.drop_constraint('uq_news_url', 'news_articles', type_='unique')
    op.drop_index('ix_news_articles_stock_id', table_name='news_articles')
    op.drop_constraint('fk_news_articles_stock_id', 'news_articles', type_='foreignkey')
    op.drop_column('news_articles', 'stock_id')
