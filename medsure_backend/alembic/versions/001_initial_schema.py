"""001_initial_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-09-30 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 0. PostgreSQL Extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm";')

    # 1. data_sources
    op.create_table(
        'data_sources',
        sa.Column('source_id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('source_name', sa.Text(), nullable=False),
        sa.Column('source_type', sa.String(length=30), nullable=False),
        sa.Column('source_url', sa.Text(), nullable=True),
        sa.Column('api_endpoint', sa.Text(), nullable=True),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('verification_status', sa.String(length=20), server_default='pending', nullable=False),
        sa.Column('coverage_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.CheckConstraint("source_type IN ('government', 'manufacturer', 'third_party', 'user_submitted', 'aggregator')", name='check_source_type'),
        sa.CheckConstraint("verification_status IN ('verified', 'pending', 'unverified')", name='check_source_verification_status'),
        sa.PrimaryKeyConstraint('source_id'),
        sa.UniqueConstraint('source_name')
    )
    op.create_index('idx_sources_name', 'data_sources', ['source_name'])
    op.create_index('idx_sources_type', 'data_sources', ['source_type'])

    # 2. manufacturers
    op.create_table(
        'manufacturers',
        sa.Column('manufacturer_id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('gstin', sa.String(length=15), nullable=True),
        sa.Column('verification_status', sa.String(length=20), server_default='pending', nullable=False),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.CheckConstraint("verification_status IN ('verified', 'pending', 'unverified')", name='check_manufacturer_verification_status'),
        sa.ForeignKeyConstraint(['source_id'], ['data_sources.source_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('manufacturer_id')
    )
    op.execute("CREATE INDEX idx_manufacturers_name ON manufacturers USING gin(to_tsvector('english', name));")
    op.execute("CREATE INDEX idx_manufacturers_name_trgm ON manufacturers USING gin(name gin_trgm_ops);")

    # 3. medicines
    op.create_table(
        'medicines',
        sa.Column('medicine_id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('generic_name', sa.Text(), nullable=False),
        sa.Column('brand_name', sa.Text(), nullable=False),
        sa.Column('dosage_form', sa.Text(), nullable=True),
        sa.Column('strength', sa.Text(), nullable=True),
        sa.Column('composition', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('therapeutic_category', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('prescription_status', sa.String(length=20), server_default='prescription', nullable=False),
        sa.Column('is_discontinued', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('confidence_score', sa.Numeric(precision=5, scale=4), server_default='0.85', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.CheckConstraint("prescription_status IN ('prescription', 'otc', 'restricted')", name='check_medicine_prescription_status'),
        sa.CheckConstraint('confidence_score >= 0 AND confidence_score <= 1', name='check_medicine_confidence_score'),
        sa.ForeignKeyConstraint(['source_id'], ['data_sources.source_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('medicine_id')
    )
    op.execute("CREATE INDEX idx_medicines_brand_name ON medicines USING gin(to_tsvector('english', brand_name));")
    op.execute("CREATE INDEX idx_medicines_generic_name ON medicines USING gin(to_tsvector('english', generic_name));")
    op.execute("CREATE INDEX idx_medicines_brand_name_trgm ON medicines USING gin(brand_name gin_trgm_ops);")
    op.execute("CREATE INDEX idx_medicines_generic_name_trgm ON medicines USING gin(generic_name gin_trgm_ops);")

    # 4. medicine_variants
    op.create_table(
        'medicine_variants',
        sa.Column('variant_id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('medicine_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('manufacturer_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('pack_size', sa.Integer(), nullable=True),
        sa.Column('unit', sa.Text(), nullable=True),
        sa.Column('packaging_description', sa.Text(), nullable=True),
        sa.Column('mrp', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('ceiling_price', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('batch_number', sa.Text(), nullable=True),
        sa.Column('expiry_date', sa.Date(), nullable=True),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['manufacturer_id'], ['manufacturers.manufacturer_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['medicine_id'], ['medicines.medicine_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_id'], ['data_sources.source_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('variant_id')
    )
    op.create_index('idx_variants_medicine_id', 'medicine_variants', ['medicine_id'])
    op.create_index('idx_variants_manufacturer_id', 'medicine_variants', ['manufacturer_id'])
    op.create_index('idx_variants_mrp', 'medicine_variants', ['mrp'])

    # 5. medicine_codes
    op.create_table(
        'medicine_codes',
        sa.Column('code_id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('variant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('gtin', sa.String(length=14), nullable=True),
        sa.Column('barcode', sa.String(length=13), nullable=True),
        sa.Column('qr_identifier', sa.Text(), nullable=True),
        sa.Column('batch_number', sa.Text(), nullable=True),
        sa.Column('serial_number', sa.Text(), nullable=True),
        sa.Column('source', sa.String(length=50), server_default='GS1', nullable=True),
        sa.Column('verified', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['variant_id'], ['medicine_variants.variant_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('code_id'),
        sa.UniqueConstraint('gtin')
    )
    op.create_index('idx_codes_gtin', 'medicine_codes', ['gtin'])
    op.create_index('idx_codes_barcode', 'medicine_codes', ['barcode'])
    op.create_index('idx_codes_variant_id', 'medicine_codes', ['variant_id'])

    # 6. medicine_images
    op.create_table(
        'medicine_images',
        sa.Column('image_id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('variant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('image_url', sa.Text(), nullable=False),
        sa.Column('image_type', sa.String(length=20), server_default='pack_front', nullable=False),
        sa.Column('source', sa.String(length=50), server_default='manufacturer', nullable=True),
        sa.Column('verified', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.CheckConstraint("image_type IN ('pack_front', 'pack_back', 'strip', 'tablet', 'bottle')", name='check_image_type'),
        sa.ForeignKeyConstraint(['variant_id'], ['medicine_variants.variant_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('image_id')
    )
    op.create_index('idx_images_variant_id', 'medicine_images', ['variant_id'])

    # 7. regulatory_alerts
    op.create_table(
        'regulatory_alerts',
        sa.Column('alert_id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('medicine_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('variant_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('alert_type', sa.String(length=30), nullable=False),
        sa.Column('batch_number', sa.Text(), nullable=True),
        sa.Column('manufacturer', sa.Text(), nullable=True),
        sa.Column('alert_date', sa.Date(), nullable=False),
        sa.Column('source_url', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('severity', sa.String(length=20), server_default='medium', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.CheckConstraint("alert_type IN ('recall', 'advisory', 'quality_alert', 'batch_alert', 'price_violation')", name='check_alert_type'),
        sa.CheckConstraint("severity IN ('critical', 'high', 'medium', 'low')", name='check_alert_severity'),
        sa.ForeignKeyConstraint(['medicine_id'], ['medicines.medicine_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['source_id'], ['data_sources.source_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['variant_id'], ['medicine_variants.variant_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('alert_id')
    )
    op.create_index('idx_alerts_medicine_id', 'regulatory_alerts', ['medicine_id'])
    op.create_index('idx_alerts_alert_date', 'regulatory_alerts', ['alert_date'])
    op.create_index('idx_alerts_severity', 'regulatory_alerts', ['severity'])
    op.create_index('idx_alerts_is_active', 'regulatory_alerts', ['is_active'])

    # 8. medicine_substitutes
    op.create_table(
        'medicine_substitutes',
        sa.Column('substitute_id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('medicine_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('substitute_medicine_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('similarity_score', sa.Numeric(precision=5, scale=4), server_default='0.80', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['medicine_id'], ['medicines.medicine_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['substitute_medicine_id'], ['medicines.medicine_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('substitute_id'),
        sa.UniqueConstraint('medicine_id', 'substitute_medicine_id', name='idx_substitutes_unique_pair')
    )
    op.create_index('idx_substitutes_medicine_id', 'medicine_substitutes', ['medicine_id'])
    op.create_index('idx_substitutes_substitute_id', 'medicine_substitutes', ['substitute_medicine_id'])


def downgrade() -> None:
    op.drop_table('medicine_substitutes')
    op.drop_table('regulatory_alerts')
    op.drop_table('medicine_images')
    op.drop_table('medicine_codes')
    op.drop_table('medicine_variants')
    op.drop_table('medicines')
    op.drop_table('manufacturers')
    op.drop_table('data_sources')
