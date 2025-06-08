#!/usr/bin/env python3
"""
Example usage of OrKa's comprehensive error handling system.

This script demonstrates how to use the error handling wrapper to get detailed
telemetry and debugging information from OrKa executions, even when they fail.
"""

import json

from orka.orchestrator import Orchestrator
from orka.orchestrator_error_wrapper import run_orchestrator_with_error_handling


async def main():
    """
    Example usage of the error handling system.
    """
    print("🚀 Starting OrKa with Comprehensive Error Handling")
    print("=" * 60)

    try:
        # Initialize orchestrator with the real config file
        orchestrator = Orchestrator("example.yml")

        # Input data for the orchestration
        input_data = {
            "user_query": "Tell me about Elon Musk and his contributions to AI",
            "context": "Technology entrepreneur analysis",
        }

        print(f"📝 Input: {input_data}")
        print("\n🔄 Running orchestration with error handling...")

        # Run with comprehensive error handling
        result = await run_orchestrator_with_error_handling(orchestrator, input_data)

        # Process the result
        print("\n📋 EXECUTION COMPLETED")
        print("=" * 30)

        if result["status"] == "success":
            print("✅ Execution completed successfully!")
            print(f"📊 Total agents executed: {result['summary']['total_agents_executed']}")
            print(f"🚨 Total errors: {result['summary']['total_errors']}")
            print(f"🔄 Total retries: {result['summary']['total_retries']}")
            print(f"📁 Report saved: {result['report_path']}")

        elif result["status"] == "critical_failure":
            print("❌ Critical failure occurred!")
            print(f"💥 Error: {result['error']}")
            print(f"📊 Logs captured: {result['logs_captured']}")
            print(f"🚨 Total errors: {len(result['error_telemetry']['errors'])}")
            print(f"📁 Error report: {result['error_report_path']}")

        # Print error telemetry summary
        error_telemetry = result.get("error_telemetry", {})
        if error_telemetry.get("errors"):
            print("\n🚨 ERROR SUMMARY")
            print("-" * 20)
            for error in error_telemetry["errors"]:
                print(f"• {error['type']} in {error['agent_id']}: {error['message']}")

        if error_telemetry.get("silent_degradations"):
            print("\n⚠️ SILENT DEGRADATIONS")
            print("-" * 25)
            for degradation in error_telemetry["silent_degradations"]:
                print(
                    f"• {degradation['type']} in {degradation['agent_id']}: {degradation['details']}",
                )

        if error_telemetry.get("retry_counters"):
            print("\n🔄 RETRY SUMMARY")
            print("-" * 18)
            for agent_id, count in error_telemetry["retry_counters"].items():
                print(f"• {agent_id}: {count} retries")

        print(f"\n📈 Execution Status: {error_telemetry.get('execution_status', 'unknown')}")

        # Show meta report if available
        if result.get("meta_report"):
            meta = result["meta_report"]
            print("\n💰 META REPORT")
            print("-" * 15)
            print(f"• Duration: {meta.get('total_duration', 0):.3f}s")
            print(f"• LLM Calls: {meta.get('total_llm_calls', 0)}")
            print(f"• Total Tokens: {meta.get('total_tokens', 0)}")
            print(f"• Total Cost: ${meta.get('total_cost_usd', 0):.6f}")
            print(f"• Avg Latency: {meta.get('avg_latency_ms', 0):.2f}ms")

    except Exception as e:
        print(f"💥 Fatal error in example script: {e}")


if __name__ == "__main__":
    # Example of what the enhanced error report JSON looks like
    example_error_report = {
        "orka_execution_report": {
            "run_id": "12345-abcde-67890",
            "timestamp": "20250608_143000",
            "execution_status": "partial",  # completed, partial, failed
            "error_telemetry": {
                "errors": [
                    {
                        "timestamp": "2025-06-08T14:30:05.123456+00:00",
                        "type": "agent_execution",
                        "agent_id": "answer_agent_1",
                        "message": "Attempt 1 failed: Connection timeout",
                        "step": 3,
                        "run_id": "12345-abcde-67890",
                        "exception": {
                            "type": "ConnectionError",
                            "message": "Connection timeout",
                            "traceback": "...",
                        },
                        "recovery_action": "retry",
                    },
                ],
                "retry_counters": {
                    "answer_agent_1": 2,
                    "eval_agent_3": 1,
                },
                "partial_successes": [
                    {
                        "timestamp": "2025-06-08T14:30:07.789012+00:00",
                        "agent_id": "answer_agent_1",
                        "retry_count": 2,
                    },
                ],
                "silent_degradations": [
                    {
                        "timestamp": "2025-06-08T14:30:10.345678+00:00",
                        "agent_id": "gpt4o_agent_2",
                        "type": "json_parsing_failure",
                        "details": "Failed to parse JSON, falling back to raw text: {invalid json...",
                    },
                ],
                "status_codes": {
                    "openai_agent_1": 200,
                    "openai_agent_2": 429,  # Rate limited
                },
                "execution_status": "partial",
                "critical_failures": [],
                "recovery_actions": [
                    {
                        "timestamp": "2025-06-08T14:30:05.123456+00:00",
                        "agent_id": "answer_agent_1",
                        "action": "retry",
                    },
                ],
            },
            "meta_report": {
                "total_duration": 15.432,
                "total_llm_calls": 8,
                "total_tokens": 12543,
                "total_cost_usd": 0.02156,
                "avg_latency_ms": 1250.5,
            },
            "execution_logs": [],  # All logged execution steps
            "total_steps_attempted": 12,
            "total_errors": 1,
            "total_retries": 3,
            "agents_with_errors": ["answer_agent_1"],
            "memory_snapshot": {
                "total_entries": 25,
                "backend_type": "RedisMemoryLogger",
            },
        },
    }

    print("📋 EXAMPLE ERROR REPORT STRUCTURE")
    print("=" * 40)
    print(json.dumps(example_error_report, indent=2)[:1000] + "...")
    print("\n🚀 Run the script with a real config to see it in action!")

    # Note: Uncomment the line below to run the actual example
    # asyncio.run(main())
