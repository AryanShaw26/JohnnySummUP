"""add_extraction_metadata

Revision ID: 31a89c8a9012
Revises: a58df5065f6d
Create Date: 2026-11-09 14:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = '31a89c8a9012'
down_revision = 'a58df5065f6d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('document_analyses', sa.Column('extraction_method', sa.String(length=40), nullable=True))
    op.add_column('document_analyses', sa.Column('extracted_page_count', sa.Integer(), nullable=True))
    op.add_column('document_analyses', sa.Column('ocr_page_count', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('document_analyses', 'ocr_page_count')
    op.drop_column('document_analyses', 'extracted_page_count')
    op.drop_column('document_analyses', 'extraction_method')
