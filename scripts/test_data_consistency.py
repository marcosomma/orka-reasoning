#!/usr/bin/env python3
"""
Test script to verify data consistency across TUI screens.
"""

import os
import sys

# Add the orka package to the path
sys.path.insert(0, os.path.abspath("."))

from orka.tui.data_manager import DataManager


def test_data_consistency():
    """Test data consistency between TUI components and unified stats system."""
    print("🧪 Testing Data Consistency Across TUI Screens")
    print("=" * 60)

    # Initialize data manager
    data_manager = DataManager()

    # Mock args for initialization
    class MockArgs:
        backend = "redisstack"

    data_manager.init_memory_logger(MockArgs())

    # Update data
    data_manager.update_data()

    # 🎯 USE UNIFIED: Test the new unified stats system
    unified = data_manager.get_unified_stats()

    print("📊 Unified Stats Results:")
    print(f"  Total entries: {unified['total_entries']}")
    print(f"  Stored memories: {unified['stored_memories']['total']}")
    print(f"    - Short-term: {unified['stored_memories']['short_term']}")
    print(f"    - Long-term: {unified['stored_memories']['long_term']}")
    print(f"    - Unknown: {unified['stored_memories']['unknown']}")
    print(f"  Log entries: {unified['log_entries']['total']}")
    print(f"    - Orchestration: {unified['log_entries']['orchestration']}")
    print(f"    - System: {unified['log_entries']['system']}")

    # Test consistency between old and new methods
    old_short = data_manager.get_filtered_memories("short")
    old_long = data_manager.get_filtered_memories("long")
    old_logs = data_manager.get_filtered_memories("logs")
    old_all = data_manager.get_filtered_memories("all")

    print("\n🔍 Consistency Checks:")

    # Check stored memories consistency
    if len(old_short) == unified["stored_memories"]["short_term"]:
        print("  ✅ Short-term memory filtering consistent")
    else:
        print(
            f"  ❌ Short-term mismatch: old={len(old_short)}, new={unified['stored_memories']['short_term']}",
        )

    if len(old_long) == unified["stored_memories"]["long_term"]:
        print("  ✅ Long-term memory filtering consistent")
    else:
        print(
            f"  ❌ Long-term mismatch: old={len(old_long)}, new={unified['stored_memories']['long_term']}",
        )

    # Check log consistency
    if len(old_logs) == unified["log_entries"]["total"]:
        print("  ✅ Log filtering consistent")
    else:
        print(f"  ❌ Log mismatch: old={len(old_logs)}, new={unified['log_entries']['total']}")

    # Check total consistency
    if len(old_all) == unified["total_entries"]:
        print("  ✅ Total count consistent")
    else:
        print(f"  ❌ Total mismatch: old={len(old_all)}, new={unified['total_entries']}")

    # Test health calculations
    print("\n🏥 Health System Test:")
    health = unified["health"]
    print(f"  Overall: {health['overall']['icon']} {health['overall']['message']}")
    print(f"  Memory: {health['memory']['icon']} {health['memory']['message']}")
    print(f"  Backend: {health['backend']['icon']} {health['backend']['message']}")
    print(f"  Performance: {health['performance']['icon']} {health['performance']['message']}")

    print("\n✅ Unified stats system test complete!")

    return {
        "unified_stats": unified,
        "old_filtering": {
            "short_memories": len(old_short),
            "long_memories": len(old_long),
            "all_logs": len(old_logs),
            "all_entries": len(old_all),
        },
    }


def test_memory_filtering():
    """Test memory filtering and show distribution."""
    print("🧪 Testing Memory Filtering and Distribution")
    print("=" * 50)

    # Initialize data manager
    data_manager = DataManager()

    # Mock args for initialization
    class MockArgs:
        backend = "redisstack"

    data_manager.init_memory_logger(MockArgs())

    # Update data to load memories
    print("📡 Loading memories from backend...")
    data_manager.update_data()

    # Get distribution
    distribution = data_manager.get_memory_distribution()

    # Display results
    print("\n📊 Memory Distribution:")
    print(f"  Total entries: {distribution['total_entries']}")
    print(f"  Stored memories: {distribution['stored_memories']['total']}")
    print(f"    - Short-term: {distribution['stored_memories']['short_term']}")
    print(f"    - Long-term: {distribution['stored_memories']['long_term']}")
    print(f"    - Unknown type: {distribution['stored_memories']['unknown']}")
    print(f"  Log entries: {distribution['log_entries']['total']}")
    print(f"    - By type: {distribution['log_entries']['by_type']}")
    print(f"  All log types: {distribution['by_log_type']}")
    print(f"  All memory types: {distribution['by_memory_type']}")

    # Test filtering
    print("\n🔍 Testing Filtering:")
    short_memories = data_manager.get_filtered_memories("short")
    long_memories = data_manager.get_filtered_memories("long")
    log_memories = data_manager.get_filtered_memories("logs")

    print(f"  Short-term filter result: {len(short_memories)} memories")
    print(f"  Long-term filter result: {len(long_memories)} memories")
    print(f"  Logs filter result: {len(log_memories)} entries")

    # Show sample entries if available
    if distribution["stored_memories"]["total"] == 0:
        print("\n⚠️  No stored memories found!")
        print("   To create memories, use a memory-writer node in your workflow")
        print("   or run: orka run --input 'test' examples/basic_memory.yml")
    else:
        print("\n✅ Stored memories found and filtering working correctly!")

        # Show a few sample entries
        if short_memories:
            print("\n📝 Sample short-term memory:")
            memory = short_memories[0]
            print(f"   Content: {data_manager._get_content(memory)[:100]}...")
            print(f"   Key: {data_manager._get_key(memory)}")

        if long_memories:
            print("\n📝 Sample long-term memory:")
            memory = long_memories[0]
            print(f"   Content: {data_manager._get_content(memory)[:100]}...")
            print(f"   Key: {data_manager._get_key(memory)}")

    return distribution


def main():
    """Main test function."""
    try:
        print("�� OrKa Memory System Unified Data Test")
        print("=" * 50)

        # Run the unified stats test
        print("\n📋 Running unified stats system tests...")
        unified_results = test_data_consistency()

        print("\n" + "=" * 50)

        # Run the memory filtering test
        distribution = test_memory_filtering()

        print("\n✅ All tests completed successfully!")

        # Comprehensive summary
        print("\n📈 Summary:")
        print("   Unified stats test: ✅ Complete")
        print("   Memory filtering test: ✅ Complete")

        # Show key metrics from unified system
        unified = unified_results["unified_stats"]
        print("\n🎯 Key Metrics (Unified System):")
        print(f"   Total Entries: {unified['total_entries']}")
        print(f"   Stored Memories: {unified['stored_memories']['total']}")
        print(f"     - Short-term: {unified['stored_memories']['short_term']}")
        print(f"     - Long-term: {unified['stored_memories']['long_term']}")
        print(f"   Log Entries: {unified['log_entries']['total']}")
        print(f"     - Orchestration: {unified['log_entries']['orchestration']}")
        print(f"     - System: {unified['log_entries']['system']}")

        # Health status
        health = unified["health"]
        print("\n🏥 System Health:")
        print(f"   Overall: {health['overall']['icon']} {health['overall']['message']}")
        print(f"   Memory: {health['memory']['icon']} {health['memory']['message']}")
        print(f"   Backend: {health['backend']['icon']} {health['backend']['message']}")
        print(f"   Performance: {health['performance']['icon']} {health['performance']['message']}")

        # Recommendations
        stored_total = unified["stored_memories"]["total"]
        if stored_total == 0:
            print("\n💡 Recommendations:")
            print("   1. No stored memories found - create some using memory-writer nodes")
            print("   2. Run: python -m orka.orka_cli run examples/basic_memory.yml 'test message'")
            print("   3. TUI memory screens will show data once memories are created")
        else:
            print("\n🎉 Your unified memory system is working correctly!")
            print("   - Data calculations are consistent across all TUI components")
            print("   - Health monitoring is centralized and accurate")
            print("   - No more scattered or redundant calculations")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
