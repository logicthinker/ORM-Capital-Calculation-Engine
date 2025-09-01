"""Add consolidation and corporate action tables

Revision ID: 003
Revises: 002
Create Date: 2025-08-29 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers
revision = '003'
down_revision = 'b45ba1e4db4c'
branch_labels = None
depends_on = None


def upgrade():
    """Create consolidation and corporate action tables"""
    
    # Create entities table
    op.create_table(
        'entities',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('entity_type', sa.String(), nullable=False),
        sa.Column('parent_entity_id', sa.String(), nullable=True),
        sa.Column('consolidation_level', sa.String(), nullable=False),
        sa.Column('rbi_entity_code', sa.String(), nullable=True),
        sa.Column('lei_code', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('incorporation_date', sa.Date(), nullable=True),
        sa.Column('regulatory_approval_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['parent_entity_id'], ['entities.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create corporate_actions table
    op.create_table(
        'corporate_actions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('action_type', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('target_entity_id', sa.String(), nullable=False),
        sa.Column('acquirer_entity_id', sa.String(), nullable=True),
        sa.Column('transaction_value', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('ownership_percentage', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('announcement_date', sa.Date(), nullable=False),
        sa.Column('rbi_approval_date', sa.Date(), nullable=True),
        sa.Column('completion_date', sa.Date(), nullable=True),
        sa.Column('effective_date', sa.Date(), nullable=False),
        sa.Column('rbi_approval_reference', sa.String(), nullable=True),
        sa.Column('requires_pillar3_disclosure', sa.Boolean(), nullable=True, default=True),
        sa.Column('disclosure_period_months', sa.Integer(), nullable=True, default=36),
        sa.Column('prior_bi_inclusion_required', sa.Boolean(), nullable=True, default=False),
        sa.Column('bi_exclusion_required', sa.Boolean(), nullable=True, default=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('additional_details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['acquirer_entity_id'], ['entities.id'], ),
        sa.ForeignKeyConstraint(['target_entity_id'], ['entities.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create consolidation_mappings table
    op.create_table(
        'consolidation_mappings',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('parent_entity_id', sa.String(), nullable=False),
        sa.Column('child_entity_id', sa.String(), nullable=False),
        sa.Column('consolidation_level', sa.String(), nullable=False),
        sa.Column('ownership_percentage', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('voting_control_percentage', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('consolidation_method', sa.String(), nullable=False),
        sa.Column('effective_from', sa.Date(), nullable=False),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['child_entity_id'], ['entities.id'], ),
        sa.ForeignKeyConstraint(['parent_entity_id'], ['entities.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for better performance
    op.create_index('idx_entities_parent_id', 'entities', ['parent_entity_id'])
    op.create_index('idx_entities_type_active', 'entities', ['entity_type', 'is_active'])
    op.create_index('idx_corporate_actions_target', 'corporate_actions', ['target_entity_id'])
    op.create_index('idx_corporate_actions_acquirer', 'corporate_actions', ['acquirer_entity_id'])
    op.create_index('idx_corporate_actions_effective_date', 'corporate_actions', ['effective_date'])
    op.create_index('idx_corporate_actions_status', 'corporate_actions', ['status'])
    op.create_index('idx_consolidation_mappings_parent', 'consolidation_mappings', ['parent_entity_id'])
    op.create_index('idx_consolidation_mappings_child', 'consolidation_mappings', ['child_entity_id'])
    op.create_index('idx_consolidation_mappings_effective', 'consolidation_mappings', ['effective_from', 'effective_to'])


def downgrade():
    """Drop consolidation and corporate action tables"""
    
    # Drop indexes
    op.drop_index('idx_consolidation_mappings_effective', table_name='consolidation_mappings')
    op.drop_index('idx_consolidation_mappings_child', table_name='consolidation_mappings')
    op.drop_index('idx_consolidation_mappings_parent', table_name='consolidation_mappings')
    op.drop_index('idx_corporate_actions_status', table_name='corporate_actions')
    op.drop_index('idx_corporate_actions_effective_date', table_name='corporate_actions')
    op.drop_index('idx_corporate_actions_acquirer', table_name='corporate_actions')
    op.drop_index('idx_corporate_actions_target', table_name='corporate_actions')
    op.drop_index('idx_entities_type_active', table_name='entities')
    op.drop_index('idx_entities_parent_id', table_name='entities')
    
    # Drop tables
    op.drop_table('consolidation_mappings')
    op.drop_table('corporate_actions')
    op.drop_table('entities')