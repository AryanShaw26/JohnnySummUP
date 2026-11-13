"""create_workspace_documents_tables

Revision ID: c81e28f3a92b
Revises: a58df5065f6d
Create Date: 2026-11-11 12:15:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = 'c81e28f3a92b'
down_revision = 'a58df5065f6d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'workspace_documents',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('workspace', sa.String(length=40), nullable=False),
        sa.Column('document_type', sa.String(length=60), nullable=False),
        sa.Column('document_subtype', sa.String(length=80), nullable=True),
        sa.Column('label', sa.String(length=255), nullable=True),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('stored_filename', sa.String(length=255), nullable=False),
        sa.Column('storage_key', sa.String(length=1024), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('file_extension', sa.String(length=15), nullable=False),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('document_date', sa.Date(), nullable=True),
        sa.Column('extraction_method', sa.String(length=30), nullable=True),
        sa.Column('page_count', sa.Integer(), server_default='1', nullable=False),
        sa.Column('character_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('status', sa.String(length=30), server_default='uploaded', nullable=False),
        sa.Column('failure_code', sa.String(length=80), nullable=True),
        sa.Column('failure_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint('file_size_bytes > 0', name='ck_workspace_documents_positive_size'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_workspace_documents_user_workspace', 'workspace_documents', ['user_id', 'workspace'], unique=False)
    op.create_index('ix_workspace_documents_user_workspace_created', 'workspace_documents', ['user_id', 'workspace', 'created_at'], unique=False)
    op.create_index('ix_workspace_documents_user_status', 'workspace_documents', ['user_id', 'status'], unique=False)
    op.create_index(op.f('ix_workspace_documents_workspace'), 'workspace_documents', ['workspace'], unique=False)
    op.create_index(op.f('ix_workspace_documents_user_id'), 'workspace_documents', ['user_id'], unique=False)

    op.create_table(
        'workspace_analyses',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('document_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('workspace', sa.String(length=40), nullable=False),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('status', sa.String(length=30), server_default='queued', nullable=False),
        sa.Column('extracted_text', sa.Text(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('structured_data', sa.JSON(), nullable=True),
        sa.Column('key_points', sa.JSON(), nullable=True),
        sa.Column('provider', sa.String(length=80), server_default='gemini', nullable=False),
        sa.Column('model_name', sa.String(length=120), nullable=True),
        sa.Column('prompt_version', sa.String(length=50), nullable=True),
        sa.Column('error_code', sa.String(length=80), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['workspace_documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('document_id', 'version', name='uq_workspace_analyses_doc_version')
    )
    op.create_index('ix_workspace_analyses_user_workspace', 'workspace_analyses', ['user_id', 'workspace'], unique=False)
    op.create_index('ix_workspace_analyses_doc_created', 'workspace_analyses', ['document_id', 'created_at'], unique=False)
    op.create_index(op.f('ix_workspace_analyses_document_id'), 'workspace_analyses', ['document_id'], unique=False)
    op.create_index(op.f('ix_workspace_analyses_user_id'), 'workspace_analyses', ['user_id'], unique=False)
    op.create_index(op.f('ix_workspace_analyses_workspace'), 'workspace_analyses', ['workspace'], unique=False)

    op.create_table(
        'workspace_findings',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('analysis_id', sa.Uuid(), nullable=False),
        sa.Column('document_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('workspace', sa.String(length=40), nullable=False),
        sa.Column('finding_type', sa.String(length=80), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=False),
        sa.Column('why_it_matters', sa.Text(), nullable=True),
        sa.Column('review_priority', sa.String(length=20), server_default='info', nullable=False),
        sa.Column('source_page', sa.Integer(), nullable=True),
        sa.Column('source_section', sa.String(length=255), nullable=True),
        sa.Column('source_excerpt', sa.Text(), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('is_reviewed', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('review_status', sa.String(length=20), server_default='pending', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['analysis_id'], ['workspace_analyses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['workspace_documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_workspace_findings_user_workspace', 'workspace_findings', ['user_id', 'workspace'], unique=False)
    op.create_index('ix_workspace_findings_doc', 'workspace_findings', ['document_id'], unique=False)
    op.create_index('ix_workspace_findings_type', 'workspace_findings', ['finding_type'], unique=False)
    op.create_index(op.f('ix_workspace_findings_analysis_id'), 'workspace_findings', ['analysis_id'], unique=False)
    op.create_index(op.f('ix_workspace_findings_document_id'), 'workspace_findings', ['document_id'], unique=False)
    op.create_index(op.f('ix_workspace_findings_user_id'), 'workspace_findings', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_workspace_findings_user_id'), table_name='workspace_findings')
    op.drop_index(op.f('ix_workspace_findings_document_id'), table_name='workspace_findings')
    op.drop_index(op.f('ix_workspace_findings_analysis_id'), table_name='workspace_findings')
    op.drop_index('ix_workspace_findings_type', table_name='workspace_findings')
    op.drop_index('ix_workspace_findings_doc', table_name='workspace_findings')
    op.drop_index('ix_workspace_findings_user_workspace', table_name='workspace_findings')
    op.drop_table('workspace_findings')

    op.drop_index(op.f('ix_workspace_analyses_workspace'), table_name='workspace_analyses')
    op.drop_index(op.f('ix_workspace_analyses_user_id'), table_name='workspace_analyses')
    op.drop_index(op.f('ix_workspace_analyses_document_id'), table_name='workspace_analyses')
    op.drop_index('ix_workspace_analyses_doc_created', table_name='workspace_analyses')
    op.drop_index('ix_workspace_analyses_user_workspace', table_name='workspace_analyses')
    op.drop_table('workspace_analyses')

    op.drop_index(op.f('ix_workspace_documents_user_id'), table_name='workspace_documents')
    op.drop_index(op.f('ix_workspace_documents_workspace'), table_name='workspace_documents')
    op.drop_index('ix_workspace_documents_user_status', table_name='workspace_documents')
    op.drop_index('ix_workspace_documents_user_workspace_created', table_name='workspace_documents')
    op.drop_index('ix_workspace_documents_user_workspace', table_name='workspace_documents')
    op.drop_table('workspace_documents')
