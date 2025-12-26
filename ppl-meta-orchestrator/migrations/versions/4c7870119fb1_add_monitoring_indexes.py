"""add monitoring indexes

Revision ID: 4c7870119fb1
Revises: b2138c29ae64
Create Date: 2025-12-26 09:33:12.728583

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4c7870119fb1'
down_revision = 'b2138c29ae64'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add performance indexes for workflow monitoring dashboard."""
    
    # WorkflowExecution indexes
    op.create_index(
        'idx_workflow_execution_status_created',
        'workflow_executions',
        ['status', 'created_at'],
        unique=False
    )
    
    op.create_index(
        'idx_workflow_execution_completed',
        'workflow_executions',
        ['status', 'completed_at'],
        unique=False
    )
    
    op.create_index(
        'idx_workflow_execution_user_status',
        'workflow_executions',
        ['user_id', 'status'],
        unique=False
    )
    
    # MethodLifecycle indexes
    op.create_index(
        'idx_method_lifecycle_status_completed',
        'method_lifecycles',
        ['status', 'completed_at'],
        unique=False
    )
    
    op.create_index(
        'idx_method_lifecycle_status_started',
        'method_lifecycles',
        ['status', 'started_at'],
        unique=False
    )
    
    op.create_index(
        'idx_method_lifecycle_method',
        'method_lifecycles',
        ['method'],
        unique=False
    )
    
    op.create_index(
        'idx_method_lifecycle_workflow_status',
        'method_lifecycles',
        ['workflow_id', 'status'],
        unique=False
    )


def downgrade() -> None:
    """Remove performance indexes."""
    
    # Drop WorkflowExecution indexes
    op.drop_index('idx_workflow_execution_status_created', table_name='workflow_executions')
    op.drop_index('idx_workflow_execution_completed', table_name='workflow_executions')
    op.drop_index('idx_workflow_execution_user_status', table_name='workflow_executions')
    
    # Drop MethodLifecycle indexes
    op.drop_index('idx_method_lifecycle_status_completed', table_name='method_lifecycles')
    op.drop_index('idx_method_lifecycle_status_started', table_name='method_lifecycles')
    op.drop_index('idx_method_lifecycle_method', table_name='method_lifecycles')
    op.drop_index('idx_method_lifecycle_workflow_status', table_name='method_lifecycles')
