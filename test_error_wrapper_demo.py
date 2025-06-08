#!/usr/bin/env python3
"""
Demonstration of OrKa's Error Wrapper with comprehensive telemetry.
"""

import asyncio

from orka.orchestrator import Orchestrator
from orka.orchestrator_error_wrapper import run_orchestrator_with_error_handling


async def demo_error_wrapper():
    """
    Demonstrate the error wrapper with comprehensive telemetry tracking.
    """
    print("🎯 ORKA ERROR WRAPPER DEMONSTRATION")
    print("=" * 60)

    # Test successful execution with telemetry
    print("\n📋 TEST: Using Error Wrapper for Comprehensive Telemetry")
    print("-" * 55)

    try:
        orchestrator = Orchestrator("example.yml")

        input_data = "What is machine learning?"

        print(f"📝 Input: {input_data}")
        print("🔄 Running with error wrapper...")

        # Use the error wrapper to get comprehensive telemetry
        result = await run_orchestrator_with_error_handling(orchestrator, input_data)

        print(f"\n✅ Execution Status: {result['status']}")

        # Display summary
        summary = result.get("summary", {})
        print(f"📊 Total agents executed: {summary.get('total_agents_executed', 0)}")
        print(f"🚨 Total errors: {summary.get('total_errors', 0)}")
        print(f"🔄 Total retries: {summary.get('total_retries', 0)}")
        print(f"📁 Report saved to: {result.get('report_path', 'N/A')}")

        # Display error telemetry details
        error_telemetry = result.get("error_telemetry", {})

        if error_telemetry.get("errors"):
            print(f"\n🚨 ERRORS DETECTED ({len(error_telemetry['errors'])})")
            print("-" * 25)
            for i, error in enumerate(error_telemetry["errors"][:3], 1):  # Show first 3
                print(f"{i}. {error['type']} in {error['agent_id']}: {error['message']}")
                if error.get("recovery_action"):
                    print(f"   🔧 Recovery: {error['recovery_action']}")

        if error_telemetry.get("silent_degradations"):
            print(f"\n⚠️ SILENT DEGRADATIONS ({len(error_telemetry['silent_degradations'])})")
            print("-" * 30)
            for i, deg in enumerate(error_telemetry["silent_degradations"][:3], 1):
                print(f"{i}. {deg['type']} in {deg['agent_id']}")
                print(f"   📝 Details: {deg['details'][:80]}...")

        if error_telemetry.get("retry_counters"):
            print("\n🔄 RETRY SUMMARY")
            print("-" * 18)
            for agent_id, count in error_telemetry["retry_counters"].items():
                print(f"• {agent_id}: {count} retries")

        if error_telemetry.get("partial_successes"):
            print(f"\n🎯 PARTIAL SUCCESSES ({len(error_telemetry['partial_successes'])})")
            print("-" * 25)
            for success in error_telemetry["partial_successes"]:
                print(f"• {success['agent_id']} succeeded after {success['retry_count']} retries")

        # Display meta report
        meta_report = result.get("meta_report", {})
        if meta_report:
            print("\n💰 META REPORT")
            print("-" * 15)
            print(f"• Duration: {meta_report.get('total_duration', 0):.3f}s")
            print(f"• LLM Calls: {meta_report.get('total_llm_calls', 0)}")
            print(f"• Total Tokens: {meta_report.get('total_tokens', 0)}")
            print(f"• Total Cost: ${meta_report.get('total_cost_usd', 0):.6f}")
            print(f"• Avg Latency: {meta_report.get('avg_latency_ms', 0):.2f}ms")

        # Display execution status
        execution_status = error_telemetry.get("execution_status", "unknown")
        status_emoji = {
            "completed": "✅",
            "partial": "⚠️",
            "failed": "❌",
        }.get(execution_status, "❓")

        print(f"\n{status_emoji} Final Status: {execution_status.upper()}")

        # Show report structure sample
        if result.get("full_report"):
            print("\n📋 FULL REPORT STRUCTURE")
            print("-" * 25)
            report_keys = list(result["full_report"].keys())[:5]
            print(f"Report sections: {', '.join(report_keys)}...")

            if "orka_execution_report" in result["full_report"]:
                exec_report = result["full_report"]["orka_execution_report"]
                print(f"• Run ID: {exec_report.get('run_id', 'N/A')}")
                print(f"• Timestamp: {exec_report.get('timestamp', 'N/A')}")
                print(f"• Total steps: {exec_report.get('total_steps_attempted', 'N/A')}")

    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback

        traceback.print_exc()

    print("\n🎉 Error wrapper demonstration completed!")


if __name__ == "__main__":
    asyncio.run(demo_error_wrapper())
