"""Create parameter governance tables

Revision ID: create_parameter_governance_tables
Revises: b45ba1e4db4c
Create Date: 2024-12-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = 'create_parameter_governance_tables'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    """Create parameter governance tables"""
    
    # Create parameter_versions table
    op.create_table('parameter_versions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('version_id', sa.String(length=36), nullable=False),
        sa.Column('model_name', sa.String(length=20), nullable=False),
        sa.Column('parameter_name', sa.String(length=100), nullable=False),
        sa.Column('parameter_type', sa.Enum('COEFFICIENT', 'THRESHOLD', 'MULTIPLIER', 'FLAG', 'MAPPING', 'FORMULA', name='parametertype'), nullable=False),
        sa.Column('parameter_category', sa.String(length=50), nullable=False),
        sa.Column('parameter_value', sa.JSON(), nullable=False),
        sa.Column('previous_value', sa.JSON(), nullable=True),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('parent_version_id', sa.String(length=36), nullable=True),
        sa.Column('status', sa.Enum('DRAFT', 'PENDING_REVIEW', 'REVIEWED', 'PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'ACTIVE', 'SUPERSEDED', name='parameterstatus'), nullable=False),
        sa.Column('effective_date', sa.Date(), nullable=False),
        sa.Column('expiry_date', sa.Date(), nullable=True),
        sa.Column('created_by', sa.String(length=100), nullable=False),
        sa.Column('reviewed_by', sa.String(length=100), nullable=True),
        sa.Column('approved_by', sa.String(length=100), nullable=True),
        sa.Column('change_reason', sa.Text(), nullable=False),
        sa.Column('business_justification', sa.Text(), nullable=False),
        sa.Column('impact_assessment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('activated_at', sa.DateTime(), nullable=True),
        sa.Column('immutable_diff', sa.Text(), nullable=True),
        sa.Column('requires_rbi_approval', sa.Boolean(), nullable=True),
        sa.Column('rbi_approval_reference', sa.String(length=100), nullable=True),
        sa.Column('disclosure_required', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['parent_version_id'], ['parameter_versions.version_id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for parameter_versions
    op.create_index('idx_param_model_name', 'parameter_versions', ['model_name', 'parameter_name'], unique=False)
    op.create_index('idx_param_status', 'parameter_versions', ['status'], unique=False)
    op.create_index('idx_param_effective', 'parameter_versions', ['effective_date'], unique=False)
    op.create_index('idx_param_version', 'parameter_versions', ['version_number'], unique=False)
    op.create_index(op.f('ix_parameter_versions_version_id'), 'parameter_versions', ['version_id'], unique=True)
    
    # Create parameter_workflow table
    op.create_table('parameter_workflow',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workflow_id', sa.String(length=36), nullable=False),
        sa.Column('parameter_version_id', sa.String(length=36), nullable=False),
        sa.Column('step_name', sa.String(length=50), nullable=False),
        sa.Column('step_status', sa.String(length=20), nullable=False),
        sa.Column('actor', sa.String(length=100), nullable=False),
        sa.Column('actor_role', sa.String(length=50), nullable=False),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('comments', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['parameter_version_id'], ['parameter_versions.version_id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for parameter_workflow
    op.create_index('idx_workflow_id', 'parameter_workflow', ['workflow_id'], unique=False)
    op.create_index('idx_workflow_status', 'parameter_workflow', ['step_status'], unique=False)
    op.create_index('idx_workflow_actor', 'parameter_workflow', ['actor'], unique=False)
    
    # Create parameter_configuration table
    op.create_table('parameter_configuration',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('model_name', sa.String(length=20), nullable=False),
        sa.Column('active_version_id', sa.String(length=36), nullable=False),
        sa.Column('configuration_name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('activated_by', sa.String(length=100), nullable=False),
        sa.Column('activated_at', sa.DateTime(), nullable=True),
        sa.Column('next_version_id', sa.String(length=36), nullable=True),
        sa.Column('next_activation_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['active_version_id'], ['parameter_versions.version_id'], ),
        sa.ForeignKeyConstraint(['next_version_id'], ['parameter_versions.version_id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for parameter_configuration
    op.create_index('idx_config_model', 'parameter_configuration', ['model_name'], unique=False)
    op.create_index('idx_config_active', 'parameter_configuration', ['active_version_id'], unique=False)


def downgrade():
    """Drop parameter governance tables"""
    
    # Drop indexes first
    op.drop_index('idx_config_active', table_name='parameter_configuration')
    op.drop_index('idx_config_model', table_name='parameter_configuration')
    op.drop_index('idx_workflow_actor', table_name='parameter_workflow')
    op.drop_index('idx_workflow_status', table_name='parameter_workflow')
    op.drop_index('idx_workflow_id', table_name='parameter_workflow')
    op.drop_index(op.f('ix_parameter_versions_version_id'), table_name='parameter_versions')
    op.drop_index('idx_param_version', table_name='parameter_versions')
    op.drop_index('idx_param_effective', table_name='parameter_versions')
    op.drop_index('idx_param_status', table_name='parameter_versions')
    op.drop_index('idx_param_model_name', table_name='parameter_versions')
    
    # Drop tables
    op.drop_table('parameter_configuration')
    op.drop_table('parameter_workflow')
    op.drop_table('parameter_versions')