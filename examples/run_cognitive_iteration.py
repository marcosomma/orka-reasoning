#!/usr/bin/env python3
"""
Test script for the Cognitive Iteration Experiment

This demonstrates the artificial deliberation concept where agents
engage in structured disagreement until reaching convergence.
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json

from orka.loader import load_configuration
from orka.orchestrator import Orchestrator


def run_cognitive_iteration_experiment(topic=None):
    """
    Run the cognitive iteration experiment with specified topic
    """
    # Load the configuration
    config_path = os.path.join(os.path.dirname(__file__), "cognitive_iteration_experiment.yml")

    try:
        config = load_configuration(config_path)
        print(f"✅ Loaded configuration: {config.get('name', 'Unknown')}")

        # Create orchestrator
        orchestrator = Orchestrator(config)

        # Prepare input
        input_data = {}
        if topic:
            input_data["topic"] = topic

        print("\n🧠 Starting cognitive iteration on topic:")
        print(f"   {topic or config.get('variables', {}).get('topic', 'Default topic')}")
        print("\n🔄 Configuration:")
        print(f"   Max iterations: {config.get('variables', {}).get('max_iterations', 7)}")
        print(
            f"   Agreement threshold: {config.get('variables', {}).get('agreement_threshold', 0.85)}",
        )

        # Run the experiment
        print("\n" + "=" * 60)
        print("🚀 LAUNCHING COGNITIVE ITERATION EXPERIMENT")
        print("=" * 60)

        result = orchestrator.run(input_data)

        print("\n" + "=" * 60)
        print("📊 EXPERIMENT RESULTS")
        print("=" * 60)

        # Extract and display key results
        if isinstance(result, dict):
            print(f"🎯 Final Agreement Score: {result.get('final_agreement_score', 'N/A')}")
            print(f"🔄 Total Iterations: {result.get('total_iterations', 'N/A')}")

            print("\n📝 Final Synthesis:")
            print("-" * 40)
            print(result.get("final_synthesis", "No synthesis available"))

            print("\n🧠 Deliberation Trace:")
            print("-" * 40)
            trace = result.get("complete_deliberation_trace", [])
            if isinstance(trace, list):
                for i, iteration in enumerate(trace, 1):
                    print(f"\nIteration {i}:")
                    if isinstance(iteration, dict):
                        for agent, stance in iteration.items():
                            if agent not in ["iteration", "timestamp"]:
                                print(f"  {agent}: {str(stance)[:100]}...")

            print("\n🎯 Convergence Path:")
            print("-" * 40)
            convergence = result.get("convergence_path", [])
            if isinstance(convergence, list):
                for i, suggestion in enumerate(convergence, 1):
                    print(f"Iteration {i}: {str(suggestion)[:150]}...")

        else:
            print("Raw result:")
            print(result)

        return result

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

    args = parser.parse_args()

    # Run experiment
    result = run_cognitive_iteration_experiment(args.topic)

    # Save results if requested
    if args.save_results and result:
        try:
            with open(args.save_results, "w") as f:
                json.dump(result, f, indent=2, default=str)
            print(f"\n💾 Results saved to: {args.save_results}")
        except Exception as e:
            print(f"❌ Failed to save results: {e}")


if __name__ == "__main__":
    main()
