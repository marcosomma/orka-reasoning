#!/usr/bin/env python3
"""
Test script to verify data consistency across TUI screens.
"""

import argparse
import os
import sys

# Add the orka package to the path
sys.path.insert(0, os.path.abspath("."))

from orka.tui.data_manager import DataManager


def test_data_consistency():
    """Test that all filtering methods return consistent results."""

    # Initialize data manager
    data_manager = DataManager()
    args = argparse.Namespace(backend="redisstack", redis_url=None)
    data_manager.init_memory_logger(args)

    print("🧪 Testing Data Consistency Across TUI Screens")
    print("=" * 60)

    # Update data
    data_manager.update_data()

    # Get all filtered data using centralized methods
    all_memories = data_manager.get_filtered_memories("all")
    short_memories = data_manager.get_filtered_memories("short")
    long_memories = data_manager.get_filtered_memories("long")
    all_logs = data_manager.get_filtered_memories("logs")

    # Count by type using centralized methods
    orchestration_logs = [
        m for m in data_manager.memory_data if data_manager._get_log_type(m) == "orchestration"
    ]
    system_logs = [
        m for m in data_manager.memory_data if data_manager._get_log_type(m) in ["log", "system"]
    ]
    memory_entries = [
        m for m in data_manager.memory_data if data_manager._get_log_type(m) == "memory"
    ]

    print("📊 Centralized Filtering Results:")
    print(f"  Total entries: {len(all_memories)}")
    print(f"  Short-term memory: {len(short_memories)}")
    print(f"  Long-term memory: {len(long_memories)}")
    print(f"  All logs: {len(all_logs)}")
    print(f"  Orchestration logs: {len(orchestration_logs)}")
    print(f"  System logs: {len(system_logs)}")
    print(f"  Memory entries: {len(memory_entries)}")
    print()

    # Verify consistency
    print("🔍 Consistency Checks:")

    # Check 1: Short + Long should equal Memory entries
    total_memory = len(short_memories) + len(long_memories)
    print(f"  Short + Long = {total_memory}, Memory entries = {len(memory_entries)}")
    if total_memory == len(memory_entries):
        print("  ✅ Memory filtering consistent")
    else:
        print("  ❌ Memory filtering inconsistent!")

    # Check 2: Orchestration + System should equal All logs
    total_logs_manual = len(orchestration_logs) + len(system_logs)
    print(f"  Orchestration + System = {total_logs_manual}, All logs = {len(all_logs)}")
    if total_logs_manual == len(all_logs):
        print("  ✅ Log filtering consistent")
    else:
        print("  ❌ Log filtering inconsistent!")

    # Check 3: All memories should equal memory + logs
    total_all_manual = len(memory_entries) + len(all_logs)
    print(f"  Memory + Logs = {total_all_manual}, All entries = {len(all_memories)}")
    if total_all_manual == len(all_memories):
        print("  ✅ Total count consistent")
    else:
        print("  ❌ Total count inconsistent!")

    print()
    print("🔧 Data Breakdown by Log Type:")
    type_counts = {}
    for memory in data_manager.memory_data:
        log_type = data_manager._get_log_type(memory)
        type_counts[log_type] = type_counts.get(log_type, 0) + 1

    for log_type, count in sorted(type_counts.items()):
        print(f"  {log_type}: {count}")

    print()
    print("✅ Data consistency test complete!")

    return {
        "all_memories": len(all_memories),
        "short_memories": len(short_memories),
        "long_memories": len(long_memories),
        "all_logs": len(all_logs),
        "orchestration_logs": len(orchestration_logs),
        "system_logs": len(system_logs),
        "memory_entries": len(memory_entries),
    }


if __name__ == "__main__":
    test_data_consistency()
