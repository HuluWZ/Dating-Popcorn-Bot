"""add_admins_table

Revision ID: 0002_add_admins_table
Revises: 0001_add_social_handle_to_review
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0002_add_admins_table'
down_revision = '0001_add_social_handle_to_review'
branch_labels = None
depends_on = None


def upgrade():
    # Create admins table
    op.create_table('admins',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('password', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )


def downgrade():
    # Drop admins table
    op.drop_table('admins')
