"""Add supervisor override tables

Revision ID: 004
Revises: 003
Create Date: 2025-08-29 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    """Create supervisor override tables"""
    
    # Create supervisor_overrides table
    op.create_table(
        'supervisor_overrides',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('override_type', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('entity_id', sa.String(), nullable=False),
        sa.Column('calculation_run_id', sa.String(), nullable=True),
        sa.Column('original_value', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('override_value', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('percentage_adjustment', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('override_reason', sa.String(), nullable=False),
        sa.Column('detailed_justification', sa.Text(), nullable=False),
        sa.Column('supporting_documentation', sa.JSON(), nullable=True),
        sa.Column('proposed_by', sa.String(), nullable=False),
        sa.Column('approved_by', sa.String(), nullable=True),
        sa.Column('approval_date', sa.Date(), nullable=True),
        sa.Column('approval_reference', sa.String(), nullable=True),
        sa.Column('effective_from', sa.Date(), nullable=False),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('requires_disclosure', sa.Boolean(), nullable=True, default=True),
        sa.Column('disclosure_period_months', sa.Integer(), nullable=True, default=12),
        sa.Column('rbi_notification_required', sa.Boolean(), nullable=True, default=True),
        sa.Column('rbi_notification_date', sa.Date(), nullable=True),
        sa.Column('rbi_notification_reference', sa.String(), nullable=True),
        sa.Column('applied_date', sa.Date(), nullable=True),
        sa.Column('applied_by', sa.String(), nullable=True),
        sa.Column('application_details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('business_context', sa.Text(), nullable=True),
        sa.Column('risk_assessment', sa.Text(), nullable=True),
        sa.Column('impact_analysis', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create override_audit_logs table
    op.create_table(
        'override_audit_logs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('override_id', sa.String(), nullable=False),
        sa.Column('action_type', sa.String(), nullable=False),
        sa.Column('action_by', sa.String(), nullable=False),
        sa.Column('action_date', sa.DateTime(), nullable=True),
        sa.Column('previous_status', sa.String(), nullable=True),
        sa.Column('new_status', sa.String(), nullable=True),
        sa.Column('changes_made', sa.JSON(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('system_context', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['override_id'], ['supervisor_overrides.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for better performance
    op.create_index('idx_supervisor_overrides_entity_id', 'supervisor_overrides', ['entity_id'])
    op.create_index('idx_supervisor_overrides_status', 'supervisor_overrides', ['status'])
    op.create_index('idx_supervisor_overrides_type', 'supervisor_overrides', ['override_type'])
    op.create_index('idx_supervisor_overrides_effective_dates', 'supervisor_overrides', ['effective_from', 'effective_to'])
    op.create_index('idx_supervisor_overrides_proposed_by', 'supervisor_overrides', ['proposed_by'])
    op.create_index('idx_supervisor_overrides_approved_by', 'supervisor_overrides', ['approved_by'])
    op.create_index('idx_override_audit_logs_override_id', 'override_audit_logs', ['override_id'])
    op.create_index('idx_override_audit_logs_action_date', 'override_audit_logs', ['action_date'])
    op.create_index('idx_override_audit_logs_action_by', 'override_audit_logs', ['action_by'])


def downgrade():
    """Drop supervisor override tables"""
    
    # Drop indexes
    op.drop_index('idx_override_audit_logs_action_by', table_name='override_audit_logs')
    op.drop_index('idx_override_audit_logs_action_date', table_name='override_audit_logs')
    op.drop_index('idx_override_audit_logs_override_id', table_name='override_audit_logs')
    op.drop_index('idx_supervisor_overrides_approved_by', table_name='supervisor_overrides')
    op.drop_index('idx_supervisor_overrides_proposed_by', table_name='supervisor_overrides')
    op.drop_index('idx_supervisor_overrides_effective_dates', table_name='supervisor_overrides')
    op.drop_index('idx_supervisor_overrides_type', table_name='supervisor_overrides')
    op.drop_index('idx_supervisor_overrides_status', table_name='supervisor_overrides')
    op.drop_index('idx_supervisor_overrides_entity_id', table_name='supervisor_overrides')
    
    # Drop tables
    op.drop_table('override_audit_logs')
    op.drop_table('supervisor_overrides')