import asyncio

import redis.asyncio as redis


async def delete_memories():
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
            return

        print(f"Found {len(all_keys)} OrKa-related keys to delete:")

        # Show what we're about to delete
        for key in sorted(all_keys):
            key_name = key.decode() if isinstance(key, bytes) else key
            key_type = await r.type(key)
            key_type_str = key_type.decode() if isinstance(key_type, bytes) else key_type
            print(f"  - {key_name} (type: {key_type_str})")

        # Ask for confirmation
        print(f"\nThis will delete {len(all_keys)} keys. Are you sure? (y/N): ", end="")

        # For script usage, we'll assume yes. Comment out these lines if you want confirmation:
        # import sys
        # response = input().strip().lower()
        # if response not in ['y', 'yes']:
        #     print("Deletion cancelled.")
        #     return

        # Delete all keys
        deleted_count = 0
        failed_count = 0

        for key in all_keys:
            try:
                result = await r.delete(key)
                if result > 0:
                    deleted_count += 1
                    key_name = key.decode() if isinstance(key, bytes) else key
                    print(f"✓ Deleted: {key_name}")
                else:
                    failed_count += 1
                    key_name = key.decode() if isinstance(key, bytes) else key
                    print(f"✗ Failed to delete: {key_name} (key may not exist)")
            except Exception as e:
                failed_count += 1
                key_name = key.decode() if isinstance(key, bytes) else key
                print(f"✗ Error deleting {key_name}: {e!s}")

        print("\nDeletion complete!")
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
            print("\n✓ All OrKa memory keys have been successfully deleted!")

    except Exception as e:
        print(f"Error during deletion process: {e!s}")
    finally:
        await r.aclose()


if __name__ == "__main__":
    asyncio.run(delete_memories())
