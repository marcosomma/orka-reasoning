#!/usr/bin/env python3
"""
Test script for the Cognitive Iteration Experiment

This demonstrates the artificial deliberation concept where agents
engage in structured disagreement until reaching convergence.
"""

import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json

from orka.loader import YAMLLoader
from orka.orchestrator import Orchestrator

SENTENCE = "Should pluto be a planet? why?"


def check_agreement_result(result):
    """
    Check if the result contains an agreement_check agent with result == True

    Args:
        result: The orchestrator result (could be dict, list, or other)

    Returns:
        bool: True if agreement is reached, False otherwise
    """
    # Convert result to JSON array if it's not already
    if not isinstance(result, list):
        if isinstance(result, dict):
            result_array = [result]
        else:
            try:
                # Try to parse as JSON if it's a string
                if isinstance(result, str):
                    parsed = json.loads(result)
                    result_array = [parsed] if not isinstance(parsed, list) else parsed
                else:
                    result_array = [result]
            except (json.JSONDecodeError, TypeError):
                result_array = [result]
    else:
        result_array = result

    # Look for agreement_check agent
    for item in result_array:
        if isinstance(item, dict) and item.get("agent_id") == "agreement_check":
            # Check the nested result structure
            agent_result = item.get("result", {})
            if isinstance(agent_result, dict):
                # Check if result.result is True
                nested_result = agent_result.get("result")
                if nested_result is True:
                    return True
                elif nested_result is False:
                    return False

    # If no agreement_check agent found, assume we need to continue
    return False


def extract_agreement_finder_response(result):
    """
    Extract the response from the agreement_finder agent to use as input for next iteration

    Args:
        result: The orchestrator result (could be dict, list, or other)

    Returns:
        str: The agreement_finder response, or None if not found
    """
    # Convert result to JSON array if it's not already
    if not isinstance(result, list):
        if isinstance(result, dict):
            result_array = [result]
        else:
            try:
                # Try to parse as JSON if it's a string
                if isinstance(result, str):
                    parsed = json.loads(result)
                    result_array = [parsed] if not isinstance(parsed, list) else parsed
                else:
                    result_array = [result]
            except (json.JSONDecodeError, TypeError):
                result_array = [result]
    else:
        result_array = result

    # Look for agreement_finder agent
    for item in result_array:
        if isinstance(item, dict) and item.get("agent_id") == "agreement_finder":
            # Check the nested structure: payload -> result -> result -> response
            payload = item.get("payload", {})
            if isinstance(payload, dict):
                first_result = payload.get("result", {})
                if isinstance(first_result, dict):
                    second_result = first_result.get("result", {})
                    if isinstance(second_result, dict):
                        response = second_result.get("response")
                        if response:
                            return str(response)

    # If no agreement_finder agent found, return None
    return None


def check_final_moderator_synthesis(result):
    """
    Check if the result contains a final_moderator_synthesis agent and extract its response

    Args:
        result: The orchestrator result (could be dict, list, or other)

    Returns:
        str: The final_moderator_synthesis response, or None if not found
    """
    # Convert result to JSON array if it's not already
    if not isinstance(result, list):
        if isinstance(result, dict):
            result_array = [result]
        else:
            try:
                # Try to parse as JSON if it's a string
                if isinstance(result, str):
                    parsed = json.loads(result)
                    result_array = [parsed] if not isinstance(parsed, list) else parsed
                else:
                    result_array = [result]
            except (json.JSONDecodeError, TypeError):
                result_array = [result]
    else:
        result_array = result

    # Look for final_moderator_synthesis agent
    for item in result_array:
        if isinstance(item, dict) and item.get("agent_id") == "final_moderator_synthesis":
            # Check the nested structure: payload -> result -> result -> response
            payload = item.get("payload", {})
            if isinstance(payload, dict):
                first_result = payload.get("result", {})
                if isinstance(first_result, dict):
                    second_result = first_result.get("result", {})
                    if isinstance(second_result, dict):
                        response = second_result.get("response")
                        if response:
                            return str(response)

    # If no final_moderator_synthesis agent found, return None
    return None


async def run_cognitive_iteration_experiment(topic=None, max_loops=10):
    """
    Run the cognitive iteration experiment with specified topic
    Continues execution until agreement_check agent returns True
    """
    # Load the configuration
    config_path = os.path.join(os.path.dirname(__file__), "cognitive_iteration_experiment.yml")

    try:
        # Load config for inspection/display purposes
        loader = YAMLLoader(config_path)
        loader.validate()
        config = loader.config
        print(f"✅ Loaded configuration: {config.get('name', 'Unknown')}")

        # Prepare input - use topic as main input string or default topic
        if not topic:
            topic = SENTENCE

        input_data = topic  # Pass the topic as the main input string

        print("\n🧠 Starting cognitive iteration on topic:")
        print(f"   {topic}")
        print("\n🔄 Configuration:")
        print(f"   Max iterations: {config.get('variables', {}).get('max_iterations', 7)}")
        print(
            f"   Agreement threshold: {config.get('variables', {}).get('agreement_threshold', 0.85)}",
        )
        print(f"   Max execution loops: {max_loops}")

        # Execution loop
        loop_count = 0
        final_result = None
        current_input = input_data  # Start with original topic

        while loop_count < max_loops:
            loop_count += 1
            print(f"\n{'=' * 60}")
            print(f"🚀 EXECUTION LOOP {loop_count}")
            print("=" * 60)
            print(f"📝 Current input: {current_input}")

            # Create orchestrator for this iteration
            orchestrator = Orchestrator(config_path)

            # Run the experiment
            result = await orchestrator.run(current_input)

            print(f"\n📊 LOOP {loop_count} RESULTS")
            print("-" * 40)

            # Check if final_moderator_synthesis is present (highest priority - immediate exit)
            final_synthesis = check_final_moderator_synthesis(result)
            if final_synthesis:
                print(f"🎉 Final moderator synthesis found after {loop_count} execution loops!")
                print(f"📝 Final synthesis: {final_synthesis}")
                final_result = result
                break

            # Check if agreement is reached
            agreement_reached = check_agreement_result(result)

            print(f"🎯 Agreement reached: {agreement_reached}")

            if agreement_reached:
                print(f"✅ Convergence achieved after {loop_count} execution loops!")
                final_result = result
                break
            else:
                print(f"🔄 Agreement not reached, continuing... (Loop {loop_count}/{max_loops})")
                final_result = result

                # Extract agreement_finder response for next iteration
                next_input = extract_agreement_finder_response(result)
                if next_input:
                    current_input = next_input
                    print(
                        f"📋 Next input extracted from agreement_finder: {current_input[:100]}...",
                    )
                else:
                    print(
                        "⚠️  No agreement_finder response found, using current input for next iteration",
                    )
                    # Keep using current_input

        if loop_count >= max_loops:
            print(f"\n⚠️  Max loops ({max_loops}) reached without convergence")

        print(f"\n{'=' * 60}")
        print("📊 FINAL EXPERIMENT RESULTS")
        print("=" * 60)
        print(f"🔄 Total execution loops: {loop_count}")

        # Check if we have final_moderator_synthesis and display it prominently
        final_synthesis_response = check_final_moderator_synthesis(final_result)
        if final_synthesis_response:
            print("\n🎉 FINAL MODERATOR SYNTHESIS:")
            print("=" * 60)
            print(final_synthesis_response)
            print("=" * 60)
            return final_synthesis_response  # Return the synthesis response directly

        # Extract and display key results
        if isinstance(final_result, dict):
            print(f"🎯 Final Agreement Score: {final_result.get('final_agreement_score', 'N/A')}")
            print(f"🔄 Total Iterations: {final_result.get('total_iterations', 'N/A')}")

            print("\n📝 Final Synthesis:")
            print("-" * 40)
            print(final_result.get("final_synthesis", "No synthesis available"))

            print("\n🧠 Deliberation Trace:")
            print("-" * 40)
            trace = final_result.get("complete_deliberation_trace", [])
            if isinstance(trace, list):
                for i, iteration in enumerate(trace, 1):
                    print(f"\nIteration {i}:")
                    if isinstance(iteration, dict):
                        for agent, stance in iteration.items():
                            if agent not in ["iteration", "timestamp"]:
                                print(f"  {agent}: {str(stance)[:100]}...")

            print("\n🎯 Convergence Path:")
            print("-" * 40)
            convergence = final_result.get("convergence_path", [])
            if isinstance(convergence, list):
                for i, suggestion in enumerate(convergence, 1):
                    print(f"Iteration {i}: {str(suggestion)[:150]}...")

        else:
            print("Raw result:")
            print(final_result)

        return final_result

    except Exception as e:
        print(f"❌ Error running experiment: {e}")
        import traceback

        traceback.print_exc()
        return None


def main():
    """
    Main function - run with custom topic or default
    """
    import argparse

    parser = argparse.ArgumentParser(description="Run Cognitive Iteration Experiment")
    parser.add_argument("--topic", "-t", type=str, help="Topic for the agents to deliberate on")
    parser.add_argument("--save-results", "-s", type=str, help="Save results to JSON file")
    parser.add_argument(
        "--max-loops",
        "-m",
        type=int,
        default=10,
        help="Maximum execution loops before stopping",
    )

    args = parser.parse_args()

    # Run experiment with execution loop
    result = asyncio.run(run_cognitive_iteration_experiment(args.topic, args.max_loops))
    print("\n\n\n\n\n>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>", result)

    # Save results if requested
    if args.save_results and result:
        try:
            with open(args.save_results, "w") as f:
                json.dump(result, f, indent=2, default=str)
            print(f"\n\n\n\n\n💾 Results saved to: {args.save_results}")
        except Exception as e:
            print(f"❌ Failed to save results: {e}")


if __name__ == "__main__":
    main()
