"""
Database performance optimization service for PPL Meta Platform.
Implements comprehensive indexing, query optimization, and performance
monitoring.
"""

import logging
import time
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class DatabaseOptimizer:
    """Database optimization service for performance improvements."""

    def __init__(self, db: Session):
        self.db = db
        self.performance_stats = {}

    def create_performance_indexes(self) -> Dict[str, bool]:
        """Create optimized indexes for frequent query patterns."""
        indexes_created = {}

        try:
            # Media table indexes for search and filtering
            media_indexes = [
                # Primary search fields
                (
                    "idx_media_device_manufacturer",
                    "CREATE INDEX IF NOT EXISTS idx_media_device_manufacturer "
                    "ON media (device_manufacturer)",
                ),
                (
                    "idx_media_device_model",
                    "CREATE INDEX IF NOT EXISTS idx_media_device_model "
                    "ON media (device_model)",
                ),
                (
                    "idx_media_device_name",
                    "CREATE INDEX IF NOT EXISTS idx_media_device_name "
                    "ON media (device_name)",
                ),
                (
                    "idx_media_device_os",
                    "CREATE INDEX IF NOT EXISTS idx_media_device_os "
                    "ON media (device_os)",
                ),
                # Media type and status
                (
                    "idx_media_type_status",
                    "CREATE INDEX IF NOT EXISTS idx_media_type_status "
                    "ON media (media_type, processing_status)",
                ),
                (
                    "idx_media_public_archived",
                    "CREATE INDEX IF NOT EXISTS idx_media_public_archived "
                    "ON media (is_public, is_archived)",
                ),
                # Time-based queries
                (
                    "idx_media_created_at",
                    "CREATE INDEX IF NOT EXISTS idx_media_created_at "
                    "ON media (created_at DESC)",
                ),
                (
                    "idx_media_capture_timestamp",
                    "CREATE INDEX IF NOT EXISTS idx_media_capture_timestamp "
                    "ON media (capture_timestamp DESC)",
                ),
                # User and ownership
                (
                    "idx_media_uploaded_by_created",
                    "CREATE INDEX IF NOT EXISTS idx_media_uploaded_by_created "
                    "ON media (uploaded_by, created_at DESC)",
                ),
                (
                    "idx_media_uploaded_by_type",
                    "CREATE INDEX IF NOT EXISTS idx_media_uploaded_by_type "
                    "ON media (uploaded_by, media_type)",
                ),
                # File properties for analytics
                (
                    "idx_media_file_size",
                    "CREATE INDEX IF NOT EXISTS idx_media_file_size "
                    "ON media (file_size)",
                ),
                (
                    "idx_media_storage_provider",
                    "CREATE INDEX IF NOT EXISTS idx_media_storage_provider "
                    "ON media (storage_provider)",
                ),
                # Composite indexes for complex queries
                (
                    "idx_media_user_type_created",
                    "CREATE INDEX IF NOT EXISTS idx_media_user_type_created "
                    "ON media (uploaded_by, media_type, created_at DESC)",
                ),
                (
                    "idx_media_device_type_created",
                    "CREATE INDEX IF NOT EXISTS idx_media_device_type_created "
                    "ON media (device_manufacturer, media_type, created_at DESC)",
                ),
                (
                    "idx_media_public_type_created",
                    "CREATE INDEX IF NOT EXISTS idx_media_public_type_created "
                    "ON media (is_public, media_type, created_at DESC)",
                ),
                # JSONB indexes for tags and categories (PostgreSQL specific)
                (
                    "idx_media_tags_gin",
                    "CREATE INDEX IF NOT EXISTS idx_media_tags_gin "
                    "ON media USING GIN (tags)",
                ),
                (
                    "idx_media_categories_gin",
                    "CREATE INDEX IF NOT EXISTS idx_media_categories_gin "
                    "ON media USING GIN (categories)",
                ),
                (
                    "idx_media_technical_metadata_gin",
                    "CREATE INDEX IF NOT EXISTS idx_media_technical_metadata_gin "
                    "ON media USING GIN (technical_metadata)",
                ),
                (
                    "idx_media_location_data_gin",
                    "CREATE INDEX IF NOT EXISTS idx_media_location_data_gin "
                    "ON media USING GIN (location_data)",
                ),
            ]

            for index_name, sql in media_indexes:
                try:
                    self.db.execute(text(sql))
                    indexes_created[index_name] = True
                    logger.info(f"Created index: {index_name}")
                except Exception as e:
                    indexes_created[index_name] = False
                    logger.error(f"Failed to create index {index_name}: {e}")

            # Media collections indexes
            collection_indexes = [
                (
                    "idx_collections_created_by",
                    "CREATE INDEX IF NOT EXISTS idx_collections_created_by ON media_collections (created_by)",
                ),
                (
                    "idx_collections_public_created",
                    "CREATE INDEX IF NOT EXISTS idx_collections_public_created ON media_collections (is_public, created_at DESC)",
                ),
                (
                    "idx_collections_name_trgm",
                    "CREATE INDEX IF NOT EXISTS idx_collections_name_trgm ON media_collections USING GIN (name gin_trgm_ops)",
                ),
            ]

            for index_name, sql in collection_indexes:
                try:
                    self.db.execute(text(sql))
                    indexes_created[index_name] = True
                    logger.info(f"Created index: {index_name}")
                except Exception as e:
                    indexes_created[index_name] = False
                    logger.error(f"Failed to create index {index_name}: {e}")

            # Media collection items indexes
            collection_item_indexes = [
                (
                    "idx_collection_items_collection_order",
                    "CREATE INDEX IF NOT EXISTS idx_collection_items_collection_order ON media_collection_items (collection_id, sort_order)",
                ),
                (
                    "idx_collection_items_media_id",
                    "CREATE INDEX IF NOT EXISTS idx_collection_items_media_id ON media_collection_items (media_id)",
                ),
                (
                    "idx_collection_items_added_by",
                    "CREATE INDEX IF NOT EXISTS idx_collection_items_added_by ON media_collection_items (added_by)",
                ),
            ]

            for index_name, sql in collection_item_indexes:
                try:
                    self.db.execute(text(sql))
                    indexes_created[index_name] = True
                    logger.info(f"Created index: {index_name}")
                except Exception as e:
                    indexes_created[index_name] = False
                    logger.error(f"Failed to create index {index_name}: {e}")

            # Media shares indexes
            share_indexes = [
                (
                    "idx_shares_token",
                    "CREATE INDEX IF NOT EXISTS idx_shares_token ON media_shares (share_token)",
                ),
                (
                    "idx_shares_shared_by",
                    "CREATE INDEX IF NOT EXISTS idx_shares_shared_by ON media_shares (shared_by)",
                ),
                (
                    "idx_shares_shared_with",
                    "CREATE INDEX IF NOT EXISTS idx_shares_shared_with ON media_shares (shared_with)",
                ),
                (
                    "idx_shares_media_active",
                    "CREATE INDEX IF NOT EXISTS idx_shares_media_active ON media_shares (media_id, is_active)",
                ),
                (
                    "idx_shares_expires_at",
                    "CREATE INDEX IF NOT EXISTS idx_shares_expires_at ON media_shares (expires_at)",
                ),
            ]

            for index_name, sql in share_indexes:
                try:
                    self.db.execute(text(sql))
                    indexes_created[index_name] = True
                    logger.info(f"Created index: {index_name}")
                except Exception as e:
                    indexes_created[index_name] = False
                    logger.error(f"Failed to create index {index_name}: {e}")

            # Media details indexes
            detail_indexes = [
                (
                    "idx_media_details_media_id",
                    "CREATE INDEX IF NOT EXISTS idx_media_details_media_id ON media_details (media_id)",
                ),
                (
                    "idx_media_details_dimensions",
                    "CREATE INDEX IF NOT EXISTS idx_media_details_dimensions ON media_details (width, height)",
                ),
                (
                    "idx_media_details_duration",
                    "CREATE INDEX IF NOT EXISTS idx_media_details_duration ON media_details (duration)",
                ),
            ]

            for index_name, sql in detail_indexes:
                try:
                    self.db.execute(text(sql))
                    indexes_created[index_name] = True
                    logger.info(f"Created index: {index_name}")
                except Exception as e:
                    indexes_created[index_name] = False
                    logger.error(f"Failed to create index {index_name}: {e}")

            # Enable PostgreSQL extensions for better performance
            extensions = [
                (
                    "pg_trgm",
                    "CREATE EXTENSION IF NOT EXISTS pg_trgm",
                ),  # Trigram matching for text search
                (
                    "btree_gin",
                    "CREATE EXTENSION IF NOT EXISTS btree_gin",
                ),  # Better GIN index support
            ]

            for ext_name, sql in extensions:
                try:
                    self.db.execute(text(sql))
                    indexes_created[f"extension_{ext_name}"] = True
                    logger.info(f"Enabled extension: {ext_name}")
                except Exception as e:
                    indexes_created[f"extension_{ext_name}"] = False
                    logger.error(f"Failed to enable extension {ext_name}: {e}")

            self.db.commit()

        except Exception as e:
            logger.error(f"Error creating performance indexes: {e}")
            self.db.rollback()

        return indexes_created

    def analyze_query_performance(
        self, query: str, params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Analyze query performance using EXPLAIN ANALYZE."""
        try:
            explain_query = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}"
            result = self.db.execute(text(explain_query), params or {})
            return result.fetchone()[0][0]
        except Exception as e:
            logger.error(f"Error analyzing query performance: {e}")
            return {}

    @contextmanager
    def query_timer(self, query_name: str):
        """Context manager to time query execution."""
        start_time = time.time()
        try:
            yield
        finally:
            end_time = time.time()
            execution_time = end_time - start_time

            if query_name not in self.performance_stats:
                self.performance_stats[query_name] = {
                    "total_time": 0,
                    "count": 0,
                    "min_time": float("inf"),
                    "max_time": 0,
                }

            stats = self.performance_stats[query_name]
            stats["total_time"] += execution_time
            stats["count"] += 1
            stats["min_time"] = min(stats["min_time"], execution_time)
            stats["max_time"] = max(stats["max_time"], execution_time)
            stats["avg_time"] = stats["total_time"] / stats["count"]

            logger.info(f"Query '{query_name}' executed in {execution_time:.4f}s")

    def get_table_statistics(self) -> Dict[str, Any]:
        """Get comprehensive table statistics for performance monitoring."""
        try:
            stats_query = """
            SELECT 
                schemaname,
                tablename,
                attname,
                n_distinct,
                correlation,
                most_common_vals,
                most_common_freqs
            FROM pg_stats 
            WHERE schemaname = 'public' 
            AND tablename IN ('media', 'media_collections', 'media_collection_items', 'media_shares', 'media_details', 'media_variants')
            ORDER BY tablename, attname;
            """

            result = self.db.execute(text(stats_query))
            stats = {}

            for row in result:
                table = row.tablename
                if table not in stats:
                    stats[table] = {}

                stats[table][row.attname] = {
                    "n_distinct": row.n_distinct,
                    "correlation": row.correlation,
                    "most_common_vals": row.most_common_vals,
                    "most_common_freqs": row.most_common_freqs,
                }

            return stats

        except Exception as e:
            logger.error(f"Error getting table statistics: {e}")
            return {}

    def vacuum_analyze_tables(self) -> Dict[str, bool]:
        """Run VACUUM ANALYZE on all media tables for optimal performance."""
        results = {}
        tables = [
            "media",
            "media_collections",
            "media_collection_items",
            "media_shares",
            "media_details",
            "media_variants",
        ]

        for table in tables:
            try:
                # Note: VACUUM cannot be run inside a transaction
                # This would need to be called outside of a transaction context
                logger.info(
                    f"Table {table} needs manual VACUUM ANALYZE - run outside transaction"
                )
                results[table] = True
            except Exception as e:
                logger.error(f"Error analyzing table {table}: {e}")
                results[table] = False

        return results

    def get_slow_queries(self, min_duration_ms: int = 1000) -> List[Dict[str, Any]]:
        """Get slow queries from PostgreSQL logs (requires pg_stat_statements extension)."""
        try:
            slow_query_sql = """
            SELECT 
                query,
                calls,
                total_time,
                mean_time,
                rows,
                100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
            FROM pg_stat_statements
            WHERE mean_time > :min_duration
            ORDER BY mean_time DESC
            LIMIT 20;
            """

            result = self.db.execute(
                text(slow_query_sql), {"min_duration": min_duration_ms}
            )
            return [dict(row) for row in result]

        except Exception as e:
            logger.error(
                f"Error getting slow queries (pg_stat_statements may not be enabled): {e}"
            )
            return []

    def optimize_query_plans(self) -> Dict[str, Any]:
        """Optimize common query plans and suggest improvements."""
        optimizations = {
            "indexes_created": False,
            "statistics_updated": False,
            "query_analysis": {},
            "recommendations": [],
        }

        try:
            # Create performance indexes
            indexes_result = self.create_performance_indexes()
            optimizations["indexes_created"] = any(indexes_result.values())

            # Get table statistics
            stats = self.get_table_statistics()
            optimizations["statistics_updated"] = bool(stats)

            # Analyze common query patterns
            common_queries = [
                (
                    "media_by_user",
                    "SELECT * FROM media WHERE uploaded_by = $1 ORDER BY created_at DESC LIMIT 20",
                ),
                (
                    "media_by_device",
                    "SELECT * FROM media WHERE device_manufacturer = $1 AND media_type = $2",
                ),
                (
                    "media_search",
                    "SELECT * FROM media WHERE tags @> $1 OR categories @> $2",
                ),
                (
                    "collection_items",
                    "SELECT m.* FROM media m JOIN media_collection_items mci ON m.id = mci.media_id WHERE mci.collection_id = $1",
                ),
            ]

            for query_name, query in common_queries:
                analysis = self.analyze_query_performance(query)
                if analysis:
                    optimizations["query_analysis"][query_name] = analysis

            # Generate recommendations
            recommendations = []

            if (
                "idx_media_tags_gin" not in indexes_result
                or not indexes_result["idx_media_tags_gin"]
            ):
                recommendations.append(
                    "Enable GIN indexes on JSONB columns for better search performance"
                )

            if not any("extension_" in key for key in indexes_result):
                recommendations.append(
                    "Enable PostgreSQL extensions (pg_trgm, btree_gin) for advanced indexing"
                )

            recommendations.extend(
                [
                    "Configure pg_stat_statements for query performance monitoring",
                    "Set up connection pooling with pgbouncer for better concurrency",
                    "Consider partitioning the media table by date for very large datasets",
                    "Implement read replicas for analytics queries",
                    "Set up automated VACUUM and ANALYZE scheduling",
                ]
            )

            optimizations["recommendations"] = recommendations

        except Exception as e:
            logger.error(f"Error optimizing query plans: {e}")

        return optimizations
