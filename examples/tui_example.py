#!/usr/bin/env python3
"""
Example demonstrating the new OrKa TUI interface modes.

This script shows how to use both Rich and Textual interfaces
with the new navigation system.
"""

import argparse
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def create_mock_args(use_textual=False, backend="redisstack", interval=2.0):
    """Create mock arguments for testing."""

    class MockArgs:
        def __init__(self):
            self.backend = backend
            self.interval = interval
            self.use_textual = use_textual
            self.textual = use_textual

    return MockArgs()


def run_rich_interface():
    """Demonstrate Rich-based interface."""
    print("🎨 Starting Rich-based interface...")
    print("Navigation:")
    print("  - View switching with 1,2,3 keys")
    print("  - Press 'q' to quit")
    print("  - Auto-refresh every 2 seconds")

    try:
        from orka.tui import ModernTUIInterface

        interface = ModernTUIInterface()
        args = create_mock_args(use_textual=False)

        print("\n✅ Rich interface initialized successfully!")
        print("Note: This would normally start the full TUI - skipping actual run for demo")

        # interface.run(args)  # Uncomment to actually run

    except Exception as e:
        print(f"❌ Error: {e}")


def run_textual_interface():
    """Demonstrate Textual-based interface."""
    print("✨ Starting Textual-native interface...")
    print("Navigation:")
    print("  1 = Dashboard")
    print("  2 = Short Memory")
    print("  3 = Long Memory")
    print("  4 = Memory Logs")
    print("  5 = Health")
    print("  q = Exit")
    print("  ^p = Command Palette")
    print("  r = Refresh")

    try:
        from orka.tui.data_manager import DataManager
        from orka.tui.textual_app import OrKaTextualApp

        # Initialize data manager
        data_manager = DataManager()

        # Create the Textual app
        app = OrKaTextualApp(data_manager)

        print("\n✅ Textual interface initialized successfully!")
        print("Note: This would normally start the full TUI - skipping actual run for demo")

        # app.run()  # Uncomment to actually run

    except ImportError:
        print("\n⚠️  Textual not available. Install with: pip install textual")
    except Exception as e:
        print(f"❌ Error: {e}")


def run_automatic_selection():
    """Demonstrate automatic interface selection."""
    print("🤖 Demonstrating automatic interface selection...")

    try:
        from orka.tui import ModernTUIInterface

        interface = ModernTUIInterface()

        # Test with Rich preference
        print("\n📱 Testing Rich mode preference...")
        args = create_mock_args(use_textual=False)
        print(f"  use_textual = {args.use_textual}")
        print("  → Would use Rich interface")

        # Test with Textual preference
        print("\n📱 Testing Textual mode preference...")
        args = create_mock_args(use_textual=True)
        print(f"  use_textual = {args.use_textual}")
        print("  → Would use Textual interface (if available)")

        # Test environment variable
        print("\n📱 Testing environment variable...")
        os.environ["ORKA_TUI_MODE"] = "textual"
        print("  ORKA_TUI_MODE = 'textual'")
        print("  → Would use Textual interface (if available)")

        # Clean up
        if "ORKA_TUI_MODE" in os.environ:
            del os.environ["ORKA_TUI_MODE"]

    except Exception as e:
        print(f"❌ Error: {e}")


def test_memory_filtering():
    """Demonstrate new memory filtering capabilities."""
    print("🔍 Testing memory filtering features...")

    try:
        from orka.tui.data_manager import DataManager

        data_manager = DataManager()

        # Test memory classification
        test_memories = [
            {"ttl": 1800, "content": "Short-term memory (30 min)"},
            {"ttl": 7200, "content": "Long-term memory (2 hours)"},
            {"ttl": None, "content": "Persistent memory"},
            {"log_type": "orchestration", "content": "System log"},
        ]

        print("\n📊 Memory classification:")
        for memory in test_memories:
            is_short = data_manager.is_short_term_memory(memory)
            memory_type = "Short-term" if is_short else "Long-term/Persistent"
            content = memory.get("content", "Unknown")
            print(f"  • {content}: {memory_type}")

        # Test filtering
        data_manager.memory_data = test_memories

        print("\n🔍 Filtering results:")
        short_memories = data_manager.get_filtered_memories("short")
        long_memories = data_manager.get_filtered_memories("long")
        log_memories = data_manager.get_filtered_memories("logs")

        print(f"  • Short-term: {len(short_memories)} entries")
        print(f"  • Long-term: {len(long_memories)} entries")
        print(f"  • Log entries: {len(log_memories)} entries")

    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    """Main demonstration function."""
    parser = argparse.ArgumentParser(description="OrKa TUI Interface Demo")
    parser.add_argument(
        "--mode",
        choices=["rich", "textual", "auto", "filter"],
        default="auto",
        help="Demo mode to run",
    )

    args = parser.parse_args()

    print("🚀 OrKa TUI Interface Demonstration")
    print("=" * 50)

    if args.mode == "rich":
        run_rich_interface()
    elif args.mode == "textual":
        run_textual_interface()
    elif args.mode == "filter":
        test_memory_filtering()
    else:
        # Run all demos
        run_rich_interface()
        print("\n" + "-" * 50 + "\n")
        run_textual_interface()
        print("\n" + "-" * 50 + "\n")
        run_automatic_selection()
        print("\n" + "-" * 50 + "\n")
        test_memory_filtering()

    print("\n" + "=" * 50)
    print("✅ Demo completed!")
    print("\nTo actually run the interfaces:")
    print("  Textual mode (default): python -m orka.orka_cli memory watch")
    print("  Rich fallback mode:     python -m orka.orka_cli memory watch --use-rich")
    print("  Basic terminal mode:    python -m orka.orka_cli memory watch --fallback")


if __name__ == "__main__":
    main()
