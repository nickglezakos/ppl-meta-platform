"""Add storage_locations table and storage fields to media

Revision ID: add_storage_locations
Revises: add_unique_collection_name, add_trigger_execution_logs_table
Create Date: 2026-04-07 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'add_storage_locations'
down_revision = (
    'add_unique_collection_name',
    'add_trigger_execution_logs_table',
)
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    insp = sa_inspect(conn)

    # --- 0. Create enum types if they don't exist ---
    locationtype = postgresql.ENUM(
        'LOCAL_DISK',
        'EXTERNAL_DRIVE',
        'CLOUD_S3',
        'CLOUD_AZURE',
        'CLOUD_GCP',
        name='locationtype',
        create_type=False,
    )
    locationtype.create(conn, checkfirst=True)

    storagetier = postgresql.ENUM(
        'ACTIVE', 'ARCHIVE',
        name='storagetier',
        create_type=False,
    )
    storagetier.create(conn, checkfirst=True)

    # --- 1. Create storage_locations table (if not exists) ---
    if 'storage_locations' not in insp.get_table_names():
        op.create_table(
            'storage_locations',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column(
                'created_at',
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=True,
            ),
            sa.Column(
                'updated_at',
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=True,
            ),
            sa.Column(
                'uuid',
                postgresql.UUID(as_uuid=True),
                nullable=True,
            ),
            sa.Column(
                'user_id',
                postgresql.UUID(as_uuid=True),
                nullable=False,
            ),
            sa.Column(
                'name', sa.String(length=255), nullable=False
            ),
            sa.Column(
                'location_type',
                locationtype,
                nullable=False,
            ),
            sa.Column(
                'base_path',
                sa.String(length=1000),
                nullable=False,
            ),
            sa.Column(
                'is_active',
                sa.Boolean(),
                nullable=False,
                server_default=sa.text('true'),
            ),
            sa.Column(
                'is_default',
                sa.Boolean(),
                nullable=False,
                server_default=sa.text('false'),
            ),
            sa.Column(
                'tier',
                storagetier,
                nullable=False,
                server_default='ACTIVE',
            ),
            sa.Column(
                'total_capacity_bytes',
                sa.BigInteger(),
                nullable=True,
            ),
            sa.Column(
                'used_bytes',
                sa.BigInteger(),
                nullable=False,
                server_default=sa.text('0'),
            ),
            sa.Column(
                'file_count',
                sa.Integer(),
                nullable=False,
                server_default=sa.text('0'),
            ),
            sa.Column(
                'cloud_config', sa.JSON(), nullable=True
            ),
            sa.Column(
                'mount_verified',
                sa.Boolean(),
                nullable=False,
                server_default=sa.text('false'),
            ),
            sa.Column(
                'last_verified_at',
                sa.DateTime(timezone=True),
                nullable=True,
            ),
            sa.Column(
                'last_scanned_at',
                sa.DateTime(timezone=True),
                nullable=True,
            ),
            sa.PrimaryKeyConstraint('id'),
        )

        op.create_index(
            'idx_storage_locations_uuid',
            'storage_locations',
            ['uuid'],
            unique=True,
        )
        op.create_index(
            'idx_storage_locations_user_id',
            'storage_locations',
            ['user_id'],
        )
        op.create_index(
            'idx_storage_locations_user_tier',
            'storage_locations',
            ['user_id', 'tier'],
        )

    # --- 2. Add storage columns to media table ---
    media_cols = {
        c['name'] for c in insp.get_columns('media')
    }
    if 'storage_uri' not in media_cols:
        op.add_column(
            'media',
            sa.Column(
                'storage_uri',
                sa.String(length=1000),
                nullable=True,
            ),
        )
    if 'storage_location_id' not in media_cols:
        op.add_column(
            'media',
            sa.Column(
                'storage_location_id',
                postgresql.UUID(as_uuid=True),
                nullable=True,
            ),
        )
        op.create_index(
            'idx_media_storage_location_id',
            'media',
            ['storage_location_id'],
        )

    # --- 3. Populate storage_uri from existing file_path ---
    op.execute(
        "UPDATE media "
        "SET storage_uri = 'file://' || file_path "
        "WHERE storage_uri IS NULL AND file_path IS NOT NULL"
    )


def downgrade():
    # Drop media columns
    op.drop_index(
        'idx_media_storage_location_id', table_name='media'
    )
    op.drop_column('media', 'storage_location_id')
    op.drop_column('media', 'storage_uri')

    # Drop storage_locations table
    op.drop_index(
        'idx_storage_locations_user_tier',
        table_name='storage_locations',
    )
    op.drop_index(
        'idx_storage_locations_user_id',
        table_name='storage_locations',
    )
    op.drop_index(
        'idx_storage_locations_uuid',
        table_name='storage_locations',
    )
    op.drop_table('storage_locations')

    # Drop enums
    sa.Enum(name='storagetier').drop(
        op.get_bind(), checkfirst=True
    )
    sa.Enum(name='locationtype').drop(
        op.get_bind(), checkfirst=True
    )
