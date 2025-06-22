import asyncio
import os
import sys

import redis.asyncio as redis

# Add the parent directory to sys.path to import orka modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from orka.memory.redis_logger import RedisMemoryLogger


async def cleanup_expired_memories():
    """Perform proper memory decay cleanup first."""
    print("=== Memory Decay Cleanup ===")

    try:
        # Create a Redis memory logger with decay enabled
        decay_config = {
            "enabled": True,
            "default_short_term_hours": 1.0,
            "default_long_term_hours": 24.0,
            "check_interval_minutes": 30,
        }

        logger = RedisMemoryLogger(decay_config=decay_config)

        # Perform cleanup of expired memories
        print("Running memory decay cleanup...")
        stats = logger.cleanup_expired_memories(dry_run=False)

        print("Decay cleanup results:")
        print(f"  - Streams processed: {stats.get('streams_processed', 0)}")
        print(f"  - Total entries checked: {stats.get('total_entries_checked', 0)}")
        print(f"  - Expired entries deleted: {stats.get('deleted_count', 0)}")
        print(f"  - Errors: {stats.get('error_count', 0)}")

        if stats.get("deleted_entries"):
            print("  - Deleted entries:")
            for entry in stats["deleted_entries"]:
                print(f"    * {entry['agent_id']} ({entry['memory_type']}) from {entry['stream']}")

        logger.client.close()
        print("[OK] Memory decay cleanup completed\n")

        return stats.get("deleted_count", 0)

    except Exception as e:
        print(f"Error during memory decay cleanup: {e}")
        return 0


async def delete_memories():
    """Delete all OrKa-related memory keys."""
    print("=== Full Memory Deletion ===")

    # Connect to Redis
    r = redis.from_url("redis://localhost:6379", decode_responses=False)

    try:
        # Get all OrKa-related keys with different patterns
        patterns = [
            "orka:memory:*",  # Memory streams
            "mem:*",  # Vector memories
            "orka:*",  # Any other OrKa keys
            "fork:*",  # Fork group keys
            "orka_*",  # Keys with orka_ prefix
        ]

        all_keys = set()
        for pattern in patterns:
            keys = await r.keys(pattern)
            all_keys.update(keys)

        if not all_keys:
            print("No OrKa memory keys found to delete.")
            return 0

        print(f"Found {len(all_keys)} OrKa-related keys to delete:")

        # Show what we're about to delete
        for key in sorted(all_keys):
            key_name = key.decode() if isinstance(key, bytes) else key
            key_type = await r.type(key)
            key_type_str = key_type.decode() if isinstance(key_type, bytes) else key_type
            print(f"  - {key_name} (type: {key_type_str})")

        # For automated cleanup (like in tests), skip confirmation
        # For manual usage, you can uncomment the confirmation code below:
        # print(f"\nThis will delete {len(all_keys)} keys. Are you sure? (y/N): ", end="")
        # import sys
        # response = input().strip().lower()
        # if response not in ['y', 'yes']:
        #     print("Deletion cancelled.")
        #     return 0

        # Delete all keys
        deleted_count = 0
        failed_count = 0

        for key in all_keys:
            try:
                result = await r.delete(key)
                if result > 0:
                    deleted_count += 1
                    key_name = key.decode() if isinstance(key, bytes) else key
                    print(f"[OK] Deleted: {key_name}")
                else:
                    failed_count += 1
                    key_name = key.decode() if isinstance(key, bytes) else key
                    print(f"[FAIL] Failed to delete: {key_name} (key may not exist)")
            except Exception as e:
                failed_count += 1
                key_name = key.decode() if isinstance(key, bytes) else key
                print(f"[ERROR] Error deleting {key_name}: {e!s}")

        print("\nFull deletion complete!")
        print(f"Successfully deleted: {deleted_count} keys")
        if failed_count > 0:
            print(f"Failed to delete: {failed_count} keys")

        # Verify deletion by checking for remaining keys
        remaining_keys = set()
        for pattern in patterns:
            keys = await r.keys(pattern)
            remaining_keys.update(keys)

        if remaining_keys:
            print(f"\nWarning: {len(remaining_keys)} keys still remain:")
            for key in remaining_keys:
                key_name = key.decode() if isinstance(key, bytes) else key
                print(f"  - {key_name}")
        else:
            print("\n[OK] All OrKa memory keys have been successfully deleted!")

        return deleted_count

    except Exception as e:
        print(f"Error during deletion process: {e!s}")
        return 0
    finally:
        await r.aclose()


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


if __name__ == "__main__":
    asyncio.run(main())
