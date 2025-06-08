#!/usr/bin/env python3
"""
Simple test of OrKa's comprehensive error handling system.
"""

import asyncio

from orka.orchestrator import Orchestrator


async def test_error_handling():
    """
    Test the error handling system with a real configuration.
    """
    print("🚀 Testing OrKa Error Handling System")
    print("=" * 50)

    try:
        # Test 1: Successful execution with real config
        print("\n📋 TEST 1: Normal Execution")
        print("-" * 25)

        orchestrator = Orchestrator("example.yml")

        input_data = "Tell me about artificial intelligence"

        print(f"📝 Input: {input_data}")
        print("🔄 Running orchestration...")

        # Run the orchestrator normally (this will show our error handling in action)
        logs = await orchestrator.run(input_data)

        print(f"✅ Successfully completed! Generated {len(logs)} log entries")

        # Check if any error telemetry was captured
        if hasattr(orchestrator, "error_telemetry"):
            telemetry = orchestrator.error_telemetry
            print(f"🚨 Errors captured: {len(telemetry.get('errors', []))}")
            print(f"🔄 Retries: {sum(telemetry.get('retry_counters', {}).values())}")
            print(f"⚠️ Silent degradations: {len(telemetry.get('silent_degradations', []))}")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()

    try:
        # Test 2: Error handling with broken config
        print("\n📋 TEST 2: Error Handling")
        print("-" * 25)

        print("🔧 Testing with non-existent config...")

        # This should trigger our error handling
        broken_orchestrator = Orchestrator("nonexistent.yml")

    except Exception as e:
        print(f"✅ Expected error caught: {type(e).__name__}: {e}")
        print("🎯 Error handling system working correctly!")

    print("\n🎉 Error handling tests completed!")


if __name__ == "__main__":
    asyncio.run(test_error_handling())
