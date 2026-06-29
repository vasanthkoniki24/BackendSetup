"""initial_auth_schema

Revision ID: e77a6835a7c8
Revises: 
Create Date: 2026-06-25 14:26:57.062796

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e77a6835a7c8'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # ------------------------------------------------------------------
    # otp_verifications — no FK dependencies, create first
    # ------------------------------------------------------------------
    op.create_table(
        'otp_verifications',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('otp', sa.String(length=10), nullable=False),
        sa.Column(
            'purpose',
            sa.Enum('REGISTRATION', 'FORGOT_PASSWORD', name='otp_purpose_enum'),
            nullable=False,
        ),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('verified', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('retry_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_otp_verifications')),
    )
    op.create_index(op.f('ix_otp_verifications_email'), 'otp_verifications', ['email'], unique=False)

    # ------------------------------------------------------------------
    # users — no FK dependencies, create before tenants + refresh_tokens
    # ------------------------------------------------------------------
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column(
            'account_type',
            sa.Enum('INDIVIDUAL', 'ORGANIZATION', name='account_type_enum'),
            nullable=False,
        ),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('is_admin', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

    # ------------------------------------------------------------------
    # refresh_tokens — FK → users.id
    # ------------------------------------------------------------------
    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('token', sa.String(length=512), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_revoked', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['user_id'], ['users.id'],
            name=op.f('fk_refresh_tokens_user_id_users'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_refresh_tokens')),
    )
    op.create_index(op.f('ix_refresh_tokens_token'), 'refresh_tokens', ['token'], unique=True)
    op.create_index(op.f('ix_refresh_tokens_user_id'), 'refresh_tokens', ['user_id'], unique=False)

    # ------------------------------------------------------------------
    # tenants — FK → users.id
    # FIX: server_default must match exact enum label 'ACTIVE' not 'active'
    # ------------------------------------------------------------------
    op.create_table(
        'tenants',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('organization_name', sa.String(length=255), nullable=False),
        sa.Column('owner_user_id', sa.String(length=36), nullable=False),
        sa.Column(
            'status',
            sa.Enum('ACTIVE', 'INACTIVE', 'SUSPENDED', name='tenant_status_enum'),
            server_default=sa.text("'ACTIVE'"),   # ← FIX: uppercase matches enum label
            nullable=False,
        ),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ['owner_user_id'], ['users.id'],
            name=op.f('fk_tenants_owner_user_id_users'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_tenants')),
    )
    op.create_index(op.f('ix_tenants_id'), 'tenants', ['id'], unique=False)
    op.create_index(op.f('ix_tenants_owner_user_id'), 'tenants', ['owner_user_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_tenants_owner_user_id'), table_name='tenants')
    op.drop_index(op.f('ix_tenants_id'), table_name='tenants')
    op.drop_table('tenants')
    op.drop_index(op.f('ix_refresh_tokens_user_id'), table_name='refresh_tokens')
    op.drop_index(op.f('ix_refresh_tokens_token'), table_name='refresh_tokens')
    op.drop_table('refresh_tokens')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    op.drop_index(op.f('ix_otp_verifications_email'), table_name='otp_verifications')
    op.drop_table('otp_verifications')
    op.execute("DROP TYPE IF EXISTS tenant_status_enum")
    op.execute("DROP TYPE IF EXISTS account_type_enum")
    op.execute("DROP TYPE IF EXISTS otp_purpose_enum")