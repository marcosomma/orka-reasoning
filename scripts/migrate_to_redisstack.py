#!/usr/bin/env python3
"""
OrKa Memory Migration Script - Legacy to RedisStack HNSW
========================================================

This script migrates existing OrKa memories from the legacy Redis system to the
enhanced RedisStack system with HNSW vector indexing.

Features:
- Migrates vector memories from "mem:" to "orka:mem:" prefix
- Ensures HNSW index is created and optimized
- Preserves all existing metadata and content
- Adds enhanced metadata for better search capabilities
- Validates migration integrity
- Provides rollback capabilities
- Supports batch processing for large datasets

Usage:
    python scripts/migrate_to_redisstack.py --dry-run
    python scripts/migrate_to_redisstack.py --migrate
    python scripts/migrate_to_redisstack.py --validate
    python scripts/migrate_to_redisstack.py --rollback
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

import redis.asyncio as redis

# Add the orka package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from orka.utils.bootstrap_memory_index import ensure_enhanced_memory_index
from orka.utils.embedder import from_bytes, get_embedder, to_bytes

logger = logging.getLogger(__name__)


class MemoryMigrator:
    """Handles migration from legacy Redis to RedisStack HNSW."""

    def __init__(self, redis_url: str = None, batch_size: int = 100):
        """
        Initialize the memory migrator.

        Args:
            redis_url: Redis connection URL
            batch_size: Number of memories to process in each batch
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.client = redis.from_url(self.redis_url, decode_responses=False)
        self.batch_size = batch_size

        # Migration tracking
        self.migration_stats = {
            "total_memories": 0,
            "migrated_memories": 0,
            "failed_migrations": 0,
            "skipped_memories": 0,
            "migration_start_time": None,
            "migration_end_time": None,
        }

        # Initialize embedder for vector validation
        self.embedder = None
        try:
            self.embedder = get_embedder()
        except Exception as e:
            logger.warning(f"Could not initialize embedder: {e}")

    async def dry_run(self) -> Dict[str, Any]:
        """
        Perform a dry run to analyze what would be migrated.

        Returns:
            Dictionary with analysis results
        """
        logger.info("Starting migration dry run...")

        # Get all legacy memory keys
        legacy_keys = await self.client.keys("mem:*")
        logger.info(f"Found {len(legacy_keys)} legacy memory entries")

        # Analyze existing enhanced memory keys
        enhanced_keys = await self.client.keys("orka:mem:*")
        logger.info(f"Found {len(enhanced_keys)} enhanced memory entries")

        # Analyze legacy memories
        analysis = {
            "legacy_memories": len(legacy_keys),
            "enhanced_memories": len(enhanced_keys),
            "namespaces": {},
            "memory_types": {},
            "size_distribution": {"small": 0, "medium": 0, "large": 0},
            "estimated_migration_time": 0,
        }

        # Sample analysis of legacy memories
        sample_size = min(50, len(legacy_keys))
        for i, key in enumerate(legacy_keys[:sample_size]):
            try:
                # Get memory data
                memory_data = await self.client.hgetall(key)
                if not memory_data:
                    continue

                # Analyze namespace
                namespace = memory_data.get(b"namespace", b"unknown").decode()
                analysis["namespaces"][namespace] = analysis["namespaces"].get(namespace, 0) + 1

                # Analyze content size
                content = memory_data.get(b"content", b"")
                content_size = len(content)
                if content_size < 100:
                    analysis["size_distribution"]["small"] += 1
                elif content_size < 1000:
                    analysis["size_distribution"]["medium"] += 1
                else:
                    analysis["size_distribution"]["large"] += 1

                # Check for existing metadata structure
                metadata = memory_data.get(b"metadata")
                if metadata:
                    try:
                        metadata_obj = json.loads(metadata.decode())
                        if "memory_type" in metadata_obj:
                            memory_type = metadata_obj["memory_type"]
                            analysis["memory_types"][memory_type] = (
                                analysis["memory_types"].get(memory_type, 0) + 1
                            )
                    except:
                        pass

            except Exception as e:
                logger.error(f"Error analyzing memory {key}: {e}")

        # Extrapolate to full dataset
        if sample_size > 0:
            scale_factor = len(legacy_keys) / sample_size
            for key in analysis["namespaces"]:
                analysis["namespaces"][key] = int(analysis["namespaces"][key] * scale_factor)
            for key in analysis["memory_types"]:
                analysis["memory_types"][key] = int(analysis["memory_types"][key] * scale_factor)
            for key in analysis["size_distribution"]:
                analysis["size_distribution"][key] = int(
                    analysis["size_distribution"][key] * scale_factor,
                )

        # Estimate migration time (approximately 10ms per memory)
        analysis["estimated_migration_time"] = len(legacy_keys) * 0.01  # seconds

        logger.info("Dry run completed")
        logger.info(f"Analysis: {json.dumps(analysis, indent=2)}")

        return analysis

    async def migrate_memories(self, force: bool = False) -> Dict[str, Any]:
        """
        Migrate memories from legacy to enhanced RedisStack system.

        Args:
            force: If True, migrate even if enhanced memories already exist

        Returns:
            Dictionary with migration results
        """
        logger.info("Starting memory migration...")
        self.migration_stats["migration_start_time"] = time.time()

        try:
            # Ensure enhanced memory index exists
            logger.info("Ensuring enhanced memory index exists...")
            index_created = await ensure_enhanced_memory_index(self.client)
            if not index_created:
                logger.error("Failed to create enhanced memory index")
                return {"error": "Failed to create enhanced memory index"}

            # Get all legacy memory keys
            legacy_keys = await self.client.keys("mem:*")
            self.migration_stats["total_memories"] = len(legacy_keys)
            logger.info(f"Found {len(legacy_keys)} legacy memories to migrate")

            if not legacy_keys:
                logger.info("No legacy memories found to migrate")
                return self.migration_stats

            # Process memories in batches
            for i in range(0, len(legacy_keys), self.batch_size):
                batch_keys = legacy_keys[i : i + self.batch_size]
                logger.info(
                    f"Processing batch {i // self.batch_size + 1}/{(len(legacy_keys) + self.batch_size - 1) // self.batch_size}",
                )

                await self._migrate_batch(batch_keys, force)

                # Brief pause between batches to avoid overwhelming Redis
                await asyncio.sleep(0.1)

            self.migration_stats["migration_end_time"] = time.time()
            migration_duration = (
                self.migration_stats["migration_end_time"]
                - self.migration_stats["migration_start_time"]
            )

            logger.info(f"Migration completed in {migration_duration:.2f} seconds")
            logger.info(f"Migrated: {self.migration_stats['migrated_memories']}")
            logger.info(f"Failed: {self.migration_stats['failed_migrations']}")
            logger.info(f"Skipped: {self.migration_stats['skipped_memories']}")

            return self.migration_stats

        except Exception as e:
            logger.error(f"Migration failed: {e}")
            self.migration_stats["error"] = str(e)
            return self.migration_stats

    async def _migrate_batch(self, batch_keys: List[bytes], force: bool) -> None:
        """Migrate a batch of memory keys."""
        for key in batch_keys:
            try:
                await self._migrate_single_memory(key, force)
            except Exception as e:
                logger.error(f"Failed to migrate memory {key}: {e}")
                self.migration_stats["failed_migrations"] += 1

    async def _migrate_single_memory(self, legacy_key: bytes, force: bool) -> None:
        """Migrate a single memory from legacy to enhanced format."""
        try:
            # Get legacy memory data
            legacy_data = await self.client.hgetall(legacy_key)
            if not legacy_data:
                logger.warning(f"Legacy memory {legacy_key} is empty, skipping")
                self.migration_stats["skipped_memories"] += 1
                return

            # Decode key and extract namespace/session info
            key_str = legacy_key.decode()
            key_parts = key_str.split(":")

            # Generate enhanced key
            if len(key_parts) >= 3:
                namespace = key_parts[1]
                timestamp_part = key_parts[2]
            else:
                namespace = "default"
                timestamp_part = str(int(time.time() * 1e6))

            enhanced_key = f"orka:mem:{namespace}:{timestamp_part}"

            # Check if enhanced version already exists
            if not force:
                existing = await self.client.exists(enhanced_key)
                if existing:
                    logger.debug(f"Enhanced memory {enhanced_key} already exists, skipping")
                    self.migration_stats["skipped_memories"] += 1
                    return

            # Prepare enhanced memory data
            enhanced_data = {}

            # Copy core fields
            core_fields = ["content", "vector", "session", "namespace", "agent", "key", "ts"]
            for field in core_fields:
                field_bytes = field.encode()
                if field_bytes in legacy_data:
                    enhanced_data[field] = legacy_data[field_bytes]

            # Process metadata and add enhancements
            metadata = {}
            if b"metadata" in legacy_data:
                try:
                    metadata = json.loads(legacy_data[b"metadata"].decode())
                except:
                    logger.warning(f"Could not parse metadata for {legacy_key}")

            # Add enhanced metadata
            current_time = datetime.now(UTC)
            enhanced_metadata = {
                **metadata,
                "migrated_at": current_time.isoformat(),
                "migration_source": "legacy_redis",
                "enhanced_version": "1.0",
                "vector_algorithm": "hnsw",
            }

            # Classify memory type and calculate importance
            content = legacy_data.get(b"content", b"").decode() if b"content" in legacy_data else ""
            memory_type = self._classify_memory_type(enhanced_metadata, content)
            importance_score = self._calculate_importance_score(content, enhanced_metadata)

            enhanced_metadata.update(
                {
                    "memory_type": memory_type,
                    "importance_score": importance_score,
                    "content_length": len(content),
                    "content_hash": hash(content),
                },
            )

            # Add enhanced fields
            enhanced_data["metadata"] = json.dumps(enhanced_metadata).encode()
            enhanced_data["memory_type"] = memory_type.encode()
            enhanced_data["importance_score"] = str(importance_score).encode()

            # Set category if not present
            if "category" not in enhanced_data:
                category = enhanced_metadata.get("category", "stored")
                enhanced_data["category"] = category.encode()

            # Calculate expiry time if decay is enabled
            expiry_time = self._calculate_expiry_time(memory_type, importance_score)
            if expiry_time:
                enhanced_data["expiry_time"] = str(int(expiry_time)).encode()

            # Validate vector data if available
            if b"vector" in enhanced_data and self.embedder:
                try:
                    vector_bytes = enhanced_data[b"vector"]
                    vector = from_bytes(vector_bytes)
                    # Re-encode to ensure consistency
                    enhanced_data[b"vector"] = to_bytes(vector)
                except Exception as e:
                    logger.warning(f"Could not validate vector for {legacy_key}: {e}")

            # Store enhanced memory
            pipe = self.client.pipeline()
            for field, value in enhanced_data.items():
                if isinstance(field, str):
                    field = field.encode()
                pipe.hset(enhanced_key, field, value)

            # Set expiry if calculated
            if expiry_time:
                expiry_seconds = max(1, int(expiry_time / 1000))
                pipe.expire(enhanced_key, expiry_seconds)

            await pipe.execute()

            logger.debug(f"Successfully migrated {legacy_key} -> {enhanced_key}")
            self.migration_stats["migrated_memories"] += 1

        except Exception as e:
            logger.error(f"Error migrating {legacy_key}: {e}")
            self.migration_stats["failed_migrations"] += 1
            raise

    def _classify_memory_type(self, metadata: Dict[str, Any], content: str) -> str:
        """Classify memory as short-term or long-term."""
        # Check if already classified
        if "memory_type" in metadata:
            return metadata["memory_type"]

        # Check category
        category = metadata.get("category", "stored")
        if category == "stored":
            # Stored memories default to long-term if substantial content
            if len(content) > 100:
                return "long_term"

        return "short_term"

    def _calculate_importance_score(self, content: str, metadata: Dict[str, Any]) -> float:
        """Calculate importance score for memory retention."""
        score = 0.5  # Base score

        # Content length factor
        if len(content) > 500:
            score += 0.2
        elif len(content) > 100:
            score += 0.1

        # Category factor
        if metadata.get("category") == "stored":
            score += 0.3

        # Query presence
        if metadata.get("query"):
            score += 0.1

        return max(0.0, min(1.0, score))

    def _calculate_expiry_time(self, memory_type: str, importance_score: float) -> Optional[int]:
        """Calculate expiry time in milliseconds."""
        # Default decay settings
        if memory_type == "long_term":
            base_hours = 24.0
        else:
            base_hours = 1.0

        # Adjust based on importance
        importance_multiplier = 1.0 + importance_score
        adjusted_hours = base_hours * importance_multiplier

        # Convert to milliseconds from now
        current_time_ms = int(time.time() * 1000)
        expiry_ms = current_time_ms + int(adjusted_hours * 3600 * 1000)

        return expiry_ms

    async def validate_migration(self) -> Dict[str, Any]:
        """
        Validate the migration by comparing legacy and enhanced memories.

        Returns:
            Validation report
        """
        logger.info("Starting migration validation...")

        validation_results = {
            "legacy_count": 0,
            "enhanced_count": 0,
            "content_matches": 0,
            "vector_matches": 0,
            "metadata_issues": 0,
            "missing_enhanced": 0,
            "validation_errors": [],
        }

        # Get all memory keys
        legacy_keys = await self.client.keys("mem:*")
        enhanced_keys = await self.client.keys("orka:mem:*")

        validation_results["legacy_count"] = len(legacy_keys)
        validation_results["enhanced_count"] = len(enhanced_keys)

        logger.info(
            f"Validating {len(legacy_keys)} legacy memories against {len(enhanced_keys)} enhanced memories",
        )

        # Validate a sample of legacy memories
        sample_size = min(100, len(legacy_keys))
        for key in legacy_keys[:sample_size]:
            try:
                await self._validate_single_memory(key, validation_results)
            except Exception as e:
                error_msg = f"Validation error for {key}: {e}"
                logger.error(error_msg)
                validation_results["validation_errors"].append(error_msg)

        # Calculate success rate
        total_checks = sample_size
        successful_checks = (
            validation_results["content_matches"] + validation_results["vector_matches"]
        ) // 2  # Each memory has both content and vector

        validation_results["success_rate"] = (
            successful_checks / total_checks if total_checks > 0 else 0
        )

        logger.info(f"Validation completed: {validation_results['success_rate']:.2%} success rate")
        return validation_results

    async def _validate_single_memory(self, legacy_key: bytes, results: Dict[str, Any]) -> None:
        """Validate a single memory migration."""
        # Get legacy data
        legacy_data = await self.client.hgetall(legacy_key)
        if not legacy_data:
            return

        # Find corresponding enhanced key
        key_str = legacy_key.decode()
        key_parts = key_str.split(":")

        if len(key_parts) >= 3:
            namespace = key_parts[1]
            timestamp_part = key_parts[2]
        else:
            namespace = "default"
            timestamp_part = str(int(time.time() * 1e6))

        enhanced_key = f"orka:mem:{namespace}:{timestamp_part}"

        # Get enhanced data
        enhanced_data = await self.client.hgetall(enhanced_key)
        if not enhanced_data:
            results["missing_enhanced"] += 1
            logger.warning(f"Enhanced memory not found for {legacy_key}")
            return

        # Validate content
        legacy_content = legacy_data.get(b"content", b"")
        enhanced_content = enhanced_data.get(b"content", b"")
        if legacy_content == enhanced_content:
            results["content_matches"] += 1
        else:
            logger.warning(f"Content mismatch for {legacy_key}")

        # Validate vector
        legacy_vector = legacy_data.get(b"vector", b"")
        enhanced_vector = enhanced_data.get(b"vector", b"")
        if legacy_vector == enhanced_vector:
            results["vector_matches"] += 1
        else:
            logger.warning(f"Vector mismatch for {legacy_key}")

        # Check enhanced metadata
        enhanced_metadata_raw = enhanced_data.get(b"metadata", b"{}")
        try:
            enhanced_metadata = json.loads(enhanced_metadata_raw.decode())
            if "migrated_at" not in enhanced_metadata:
                results["metadata_issues"] += 1
        except:
            results["metadata_issues"] += 1

    async def rollback_migration(self, confirm: bool = False) -> Dict[str, Any]:
        """
        Rollback migration by removing enhanced memories.

        Args:
            confirm: If True, actually perform the rollback

        Returns:
            Rollback report
        """
        if not confirm:
            logger.warning(
                "Rollback requested but not confirmed. Use --confirm to actually rollback.",
            )
            return {"error": "Rollback not confirmed"}

        logger.info("Starting migration rollback...")

        # Get all enhanced memory keys
        enhanced_keys = await self.client.keys("orka:mem:*")
        logger.info(f"Found {len(enhanced_keys)} enhanced memories to remove")

        rollback_stats = {
            "total_enhanced": len(enhanced_keys),
            "removed_memories": 0,
            "removal_errors": 0,
        }

        # Remove enhanced memories in batches
        for i in range(0, len(enhanced_keys), self.batch_size):
            batch_keys = enhanced_keys[i : i + self.batch_size]

            try:
                deleted_count = await self.client.delete(*batch_keys)
                rollback_stats["removed_memories"] += deleted_count
                logger.info(
                    f"Removed batch {i // self.batch_size + 1}/{(len(enhanced_keys) + self.batch_size - 1) // self.batch_size}",
                )
            except Exception as e:
                logger.error(f"Error removing batch: {e}")
                rollback_stats["removal_errors"] += len(batch_keys)

        logger.info(f"Rollback completed. Removed {rollback_stats['removed_memories']} memories")
        return rollback_stats

    async def close(self):
        """Close Redis connection."""
        await self.client.close()


async def main():
    """Main migration script entry point."""
    parser = argparse.ArgumentParser(description="OrKa Memory Migration Tool")
    parser.add_argument("--redis-url", help="Redis connection URL")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size for processing")
    parser.add_argument("--dry-run", action="store_true", help="Analyze what would be migrated")
    parser.add_argument("--migrate", action="store_true", help="Perform the migration")
    parser.add_argument("--validate", action="store_true", help="Validate the migration")
    parser.add_argument("--rollback", action="store_true", help="Rollback the migration")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force migration even if enhanced memories exist",
    )
    parser.add_argument("--confirm", action="store_true", help="Confirm destructive operations")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create migrator
    migrator = MemoryMigrator(redis_url=args.redis_url, batch_size=args.batch_size)

    try:
        if args.dry_run:
            results = await migrator.dry_run()
            print("\n=== Migration Analysis ===")
            print(json.dumps(results, indent=2))

        elif args.migrate:
            results = await migrator.migrate_memories(force=args.force)
            print("\n=== Migration Results ===")
            print(json.dumps(results, indent=2))

        elif args.validate:
            results = await migrator.validate_migration()
            print("\n=== Validation Results ===")
            print(json.dumps(results, indent=2))

        elif args.rollback:
            results = await migrator.rollback_migration(confirm=args.confirm)
            print("\n=== Rollback Results ===")
            print(json.dumps(results, indent=2))

        else:
            parser.print_help()
            print("\nExample usage:")
            print("  python scripts/migrate_to_redisstack.py --dry-run")
            print("  python scripts/migrate_to_redisstack.py --migrate")
            print("  python scripts/migrate_to_redisstack.py --validate")
            print("  python scripts/migrate_to_redisstack.py --rollback --confirm")

    finally:
        await migrator.close()


if __name__ == "__main__":
    asyncio.run(main())
