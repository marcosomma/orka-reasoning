import asyncio
import os
import sys

import redis.asyncio as redis

# Add the parent directory to sys.path to import orka modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from orka.memory_logger import create_memory_logger


async def cleanup_expired_memories():
    """Perform proper memory decay cleanup first."""
    print("=== Memory Decay Cleanup ===")

    try:
        # Create a RedisStack memory logger with decay enabled
        decay_config = {
            "enabled": True,
            "default_short_term_hours": 1.0,
            "default_long_term_hours": 24.0,
            "check_interval_minutes": 30,
        }

        # Use the factory to create the proper logger (RedisStack)
        logger = create_memory_logger(
            backend="redisstack",
            redis_url="redis://localhost:6380/0",
            decay_config=decay_config,
        )

        # Perform cleanup of expired memories
        print("Running memory decay cleanup...")
        stats = logger.cleanup_expired_memories(dry_run=False)

        print("Decay cleanup results:")
        print(f"  - Total checked: {stats.get('total_checked', 0)}")
        print(f"  - Expired found: {stats.get('expired_found', 0)}")
        print(f"  - Cleaned: {stats.get('cleaned', 0)}")
        print(f"  - Errors: {len(stats.get('errors', []))}")

        if stats.get("errors"):
            print("  - Errors:")
            for error in stats["errors"][:5]:  # Show first 5 errors
                print(f"    * {error}")

        logger.close()
        print("[OK] Memory decay cleanup completed\n")

        return stats.get("cleaned", 0)

    except Exception as e:
        print(f"Error during memory decay cleanup: {e}")
        return 0


async def delete_memories():
    """Delete all OrKa-related memory keys from both Redis instances."""
    print("=== Full Memory Deletion ===")

    # Connect to both Redis instances (6379 for legacy, 6380 for RedisStack)
    redis_instances = [
        ("redis://localhost:6379", "Legacy Redis (6379)"),
        ("redis://localhost:6380", "RedisStack (6380)"),
    ]

    total_deleted = 0

    for redis_url, description in redis_instances:
        print(f"\n--- Cleaning {description} ---")

        try:
            r = redis.from_url(redis_url, decode_responses=False)

            # Test connection
            await r.ping()
            print(f"[OK] Connected to {description}")

        except Exception as e:
            print(f"[SKIP] Cannot connect to {description}: {e}")
            continue

        try:
            # Get all OrKa-related keys with comprehensive patterns
            patterns = [
                "orka:memory:*",  # Legacy memory streams
                "orka_memory:*",  # New RedisStack memory entries
                "mem:*",  # Vector memories
                "orka:*",  # Any other OrKa keys
                "fork:*",  # Fork group keys
                "orka_*",  # Keys with orka_ prefix
                "enhanced_memory_idx",  # RedisStack search index
                "orka_enhanced_memory",  # Enhanced memory index
                "*memory*orka*",  # Any memory-related OrKa keys
                "*orka*memory*",  # Any OrKa-related memory keys
            ]

            all_keys = set()
            for pattern in patterns:
                try:
                    keys = await r.keys(pattern)
                    all_keys.update(keys)
                except Exception as e:
                    print(f"[WARN] Error searching pattern {pattern}: {e}")

            if not all_keys:
                print(f"No OrKa memory keys found in {description}.")
                await r.aclose()
                continue

            print(f"Found {len(all_keys)} OrKa-related keys in {description}:")

            # Show what we're about to delete (limit to first 20 for readability)
            keys_to_show = sorted(all_keys)[:20]
            for key in keys_to_show:
                try:
                    key_name = key.decode() if isinstance(key, bytes) else key
                    key_type = await r.type(key)
                    key_type_str = key_type.decode() if isinstance(key_type, bytes) else key_type
                    print(f"  - {key_name} (type: {key_type_str})")
                except Exception:
                    print(f"  - {key} (unknown type)")

            if len(all_keys) > 20:
                print(f"  ... and {len(all_keys) - 20} more keys")

            # Delete all keys
            deleted_count = 0
            failed_count = 0

            # Delete in batches for better performance
            key_list = list(all_keys)
            batch_size = 100

            for i in range(0, len(key_list), batch_size):
                batch = key_list[i : i + batch_size]
                try:
                    # Use pipeline for batch deletion
                    pipe = r.pipeline()
                    for key in batch:
                        pipe.delete(key)
                    results = await pipe.execute()

                    batch_deleted = sum(1 for result in results if result > 0)
                    batch_failed = len(results) - batch_deleted

                    deleted_count += batch_deleted
                    failed_count += batch_failed

                    print(
                        f"[OK] Batch {i // batch_size + 1}: Deleted {batch_deleted}, Failed {batch_failed}",
                    )

                except Exception as e:
                    failed_count += len(batch)
                    print(f"[ERROR] Batch deletion failed: {e}")

            print(f"\nDeletion complete for {description}!")
            print(f"Successfully deleted: {deleted_count} keys")
            if failed_count > 0:
                print(f"Failed to delete: {failed_count} keys")

            # Verify deletion by checking for remaining keys
            remaining_keys = set()
            for pattern in patterns:
                try:
                    keys = await r.keys(pattern)
                    remaining_keys.update(keys)
                except Exception:
                    pass

            if remaining_keys:
                print(f"\nWarning: {len(remaining_keys)} keys still remain in {description}:")
                for key in list(remaining_keys)[:10]:  # Show first 10
                    key_name = key.decode() if isinstance(key, bytes) else key
                    print(f"  - {key_name}")
                if len(remaining_keys) > 10:
                    print(f"  ... and {len(remaining_keys) - 10} more")
            else:
                print(
                    f"\n[OK] All OrKa memory keys have been successfully deleted from {description}!",
                )

            total_deleted += deleted_count

        except Exception as e:
            print(f"Error during deletion process for {description}: {e!s}")
        finally:
            await r.aclose()

    return total_deleted


async def main():
    """Main function that performs both decay cleanup and full deletion."""
    print("OrKa Memory Cleanup Script")
    print("=" * 50)

    # Step 1: Perform proper memory decay cleanup first
    decay_deleted = await cleanup_expired_memories()

    # Step 2: Perform full deletion of all remaining OrKa keys
    full_deleted = await delete_memories()

    print("\n" + "=" * 50)
    print("CLEANUP SUMMARY")
    print(f"Expired memories removed by decay cleanup: {decay_deleted}")
    print(f"Total keys removed by full deletion: {full_deleted}")
    print("[OK] Memory cleanup completed successfully!")

    if full_deleted == 0 and decay_deleted == 0:
        print("\n[INFO] No memories found to delete. System is already clean!")


if __name__ == "__main__":
    asyncio.run(main())
