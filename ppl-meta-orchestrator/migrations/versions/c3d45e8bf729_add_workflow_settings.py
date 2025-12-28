"""Add workflow settings table

Revision ID: c3d45e8bf729
Revises: 4c7870119fb1
Create Date: 2024-12-28 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = 'c3d45e8bf729'
down_revision = '4c7870119fb1'
branch_labels = None
depends_on = None


def upgrade():
    """Create workflow_settings table for configurable workflow parameters."""
    
    op.create_table(
        'workflow_settings',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('setting_key', sa.String(255), unique=True, nullable=False),
        sa.Column('setting_value', sa.Float(), nullable=False),
        sa.Column('min_value', sa.Float(), nullable=True),
        sa.Column('max_value', sa.Float(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('updated_by', sa.String(255), nullable=True),
    )
    
    # Create index on setting_key for fast lookups
    op.create_index('idx_workflow_settings_key', 'workflow_settings', ['setting_key'])
    
    # Insert default velocity_sensitivity setting
    op.execute(
        text("""
            INSERT INTO workflow_settings 
            (setting_key, setting_value, min_value, max_value, description, updated_by) 
            VALUES 
            ('velocity_sensitivity', 20.0, 5.0, 50.0, 
             'Face tracking tolerance percentage for temporal grouping across video frames. Controls how much movement is allowed between frames when grouping faces as the same person.', 
             'system')
        """)
    )


def downgrade():
    """Drop workflow_settings table."""
    
    op.drop_index('idx_workflow_settings_key', table_name='workflow_settings')
    op.drop_table('workflow_settings')
