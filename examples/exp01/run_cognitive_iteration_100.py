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
from datetime import UTC, datetime

from orka.loader import YAMLLoader
from orka.orchestrator import Orchestrator

# Global variables to track execution state
LOOP_COUNT = 0
CURRENT_INDEX = 0

SENTENCE = "Should pluto be a planet? why?"
QUESTIONS = [
    "Should child-free adults pay a school tax surcharge?",
    "Legalise gene-editing embryos for IQ enhancement?",
    "Make nuclear power the primary climate lever for 30 years?",
    "Grant legal personhood to great apes?",
    "Ban facial recognition in all public spaces?",
    "Require real-name verification for social-media posting?",
    "Enforce a four-day work-week by law?",
    "Compel organ donation at death (opt-out system)?",
    "Treat AI companions as regulated mental-health devices?",
    "Nationalise all for-profit elder-care homes.",
    "Use brain–computer interfaces to rehabilitate violent offenders.",
    "Phase out meat consumption worldwide by 2040.",
    "Impose a global wealth tax above $50 million.",
    "Replace standardised exams with portfolio-only admissions.",
    "Require open publication of LLM training data.",
    "Grant AI systems the right to hold patents.",
    "Deploy stratospheric aerosol geo-engineering now.",
    "Abolish legacy admissions at universities overnight.",
    "Mandate cashless economies—ban paper money.",
    "Criminalise dead-naming as hate speech.",
    "Declare the internet a human right with free baseline service.",
    "Ban crypto mining in countries with energy shortages.",
    "Implement a global fertility cap: two children per person.",
    "Give space-mining profits to a UN trust fund, not companies.",
    "Compulsory national service (civil or military) at 18.",
    "Outlaw single-family zoning in cities over 100 k population.",
    "Open-source biolab hardware: publish or restrict?",
    "Weight votes by expertise on technical referenda.",
    "Ban algorithmic parole decisions for bias concerns.",
    "Force all political ads through AI fact-checking pre-release.",
    "Replace paper ballots with blockchain voting.",
    "Allow deep-fake creators to be sued under strict liability.",
    "License voice-cloning tech with mandatory watermarking.",
    "Cap algorithmic trading speed to milliseconds.",
    "Recognise memetic warfare as a war crime.",
    'Tax private space-launches for "sky commons" use.',
    "Deploy lethal autonomous drones for UN peacekeeping.",
    "Ban open-source malware publication.",
    "Treat crypto anonymity tools as protected speech.",
    "Introduce digital detox tax credits.",
    "Require carbon-removal-only subsidies—end renewables aid.",
    "Criminalise facial-age filters that target minors.",
    "Make AI emotion detection illegal in hiring.",
    "Mandate ethical review boards for influencer sponsorship deals.",
    "Allow sentencing algorithms to override judicial discretion.",
    "Grant climate refugees automatic citizenship.",
    "License synthetic biology start-ups like nuclear facilities.",
    "Recognise e-sports as Olympic disciplines.",
    "Ban single-use fashion under environmental law.",
    "Require smart-city residents to share location in real time.",
    "Outlaw antibiotic use in livestock entirely.",
    "Replace live teachers with AI tutors for core subjects.",
    "Impose a global moratorium on deep-sea mining.",
    "Make data localisation mandatory for personal data.",
    "Introduce attention-span metrics as public-health targets.",
    "Let AI decide battlefield triage to remove bias.",
    "Add warning labels to immersive VR for psychological risk.",
    "Ban dark-pattern UX under consumer-protection law.",
    "Require satellite constellations to pay light-pollution fees.",
    "Prohibit algorithmic micro-targeting in political campaigns.",
    "Treat privacy breaches as human-rights violations.",
    "Allow paid organ markets under strict regulation.",
    "Set a global moratorium on AGI research until governance is ready.",
    "Mandate vaccination passports for all international travel.",
    "Abolish tuition—make public universities tax-funded only.",
    "Grant voting rights to 16-year-olds.",
    "Treat synthetic food as equivalent to conventional—no labels.",
    "Ban gig-economy platforms from classifying workers as contractors.",
    "Require algorithmic audits to be public and reproducible.",
    "Make AI-generated novels eligible for literary prizes.",
    "Outlaw pay-to-win mechanics in games aimed at minors.",
    "Force companies to share AI model weights after market dominance.",
    "Introduce mandatory coding education from age six worldwide.",
    'Levy a "plastic footprint" tax on consumer goods.',
    "Recognise smart-contract weapons as WMD equivalents.",
    "Make deep-fake pornography a federal felony.",
    "Require real-time CO₂ labels on online purchases.",
    "Ban private cars from city centres over 1 million residents.",
    "Give AI ethics boards veto power over product launches.",
    "Regulate digital resurrection of celebrities—family consent only?",
    "Require income transparency for all political candidates.",
    "Ban lab-grown meat until long-term studies complete.",
    "Make mental-health screening compulsory in schools.",
    "Outlaw single-click subscriptions without equal-ease cancellation.",
    "Limit extreme-longevity research funding until poverty eradication.",
    "Treat augmented-reality eyewear as surveillance devices.",
    "Mandate public, plain-text EULAs for every software update.",
    "Ban stock buybacks in companies receiving climate subsidies.",
    "Require AI watermarking in all generated media.",
    "Recognise space-debris creation as an international tort.",
    "Make social-credit scoring illegal in financial services.",
    'Grant sentient AI (if any) "minor" legal status.',
    "Require peer-reviewed impact studies before big-tech acquisitions.",
    "Ban predictive policing algorithms.",
    "Levy a luxury carbon tax on private jets and yachts.",
    "Replace income tax with a data-usage tax.",
    "Mandate public APIs for dominant social platforms.",
    "Require AI moderators to publish training data for transparency.",
    "Ban micro-targeted health ads based on genetic data.",
    "Create a UN-style oversight body for the Metaverse before mass rollout.",
]


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


async def run_cognitive_iteration_experiment(
    topic=None,
    max_loops=10,
    is_a_question=False,
    local_run=False,
):
    """
    Run the cognitive iteration experiment with specified topic
    Continues execution until agreement_check agent returns True
    """
    global LOOP_COUNT

    # Load the configuration
    file = None
    if not local_run:
        file = (
            "cognitive_iteration_experiment_opinion.yml"
            if not is_a_question
            else "cognitive_iteration_experiment_answer.yml"
        )
    else:
        file = "cognitive_iteration_experiment_opinion_local.yml"
    config_path = os.path.join(os.path.dirname(__file__), file)

    try:
        # Load config for inspection/display purposes
        loader = YAMLLoader(config_path)
        loader.validate()
        config = loader.config
        print(f"✅ Loaded configuration: {file}")

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
        final_result = None
        current_input = input_data  # Start with original topic
        loop_count = 0  # Initialize local loop counter

        while loop_count < max_loops:
            loop_count += 1
            LOOP_COUNT = loop_count  # Sync global counter
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
                LOOP_COUNT = loop_count  # Final sync of global counter
                break

            # Check if agreement is reached
            agreement_reached = check_agreement_result(result)

            print(f"🎯 Agreement reached: {agreement_reached}")

            if agreement_reached:
                print(f"✅ Convergence achieved after {loop_count} execution loops!")
                final_result = result
                LOOP_COUNT = loop_count  # Final sync of global counter
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

        # Final sync of global counter (in case we exit due to max loops)
        LOOP_COUNT = loop_count

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
    global LOOP_COUNT, CURRENT_INDEX

    import argparse

    parser = argparse.ArgumentParser(description="Run Cognitive Iteration Experiment")
    parser.add_argument("--topic", "-t", type=str, help="Topic for the agents to deliberate on")
    parser.add_argument("--local", "-l", type=bool, help="Use local models")
    parser.add_argument("--question", "-q", type=bool, help="Mark as a question")
    parser.add_argument("--save-results", "-s", type=str, help="Save results to JSON file")
    parser.add_argument(
        "--max-loops",
        "-m",
        type=int,
        default=100,
        help="Maximum execution loops before stopping",
    )

    args = parser.parse_args()

    # If a specific topic is provided, run just that one
    if args.topic:
        CURRENT_INDEX = 1
        LOOP_COUNT = 0  # Reset loop count for this run

        print(f"\n🎯 Running single experiment with topic: {args.topic}")
        result = asyncio.run(
            run_cognitive_iteration_experiment(
                args.topic,
                args.max_loops,
                args.question,
                args.local,
            ),
        )

        # Save results if requested
        if args.save_results and result:
            try:
                with open(f"{args.save_results}_single", "w") as f:
                    to_save = {
                        "run": CURRENT_INDEX,
                        "topic": args.topic,
                        "loops": LOOP_COUNT,
                        "result": result,
                    }
                    json.dump(to_save, f, indent=2, default=str)
                    print(f"✅ Results saved to {args.save_results}_single")
            except Exception as e:
                print(f"❌ Failed to save results: {e}")
        return

    # Run all questions in the list
    print(f"\n🎯 Running {len(QUESTIONS)} experiments...")

    for index, sentence in enumerate(QUESTIONS, 1):
        CURRENT_INDEX = index
        LOOP_COUNT = 0  # Reset loop count for each experiment

        print(f"\n{'=' * 80}")
        print(f"🚀 EXPERIMENT {index}/{len(QUESTIONS)}")
        print(f"📝 Topic: {sentence}")
        print("=" * 80)

        # Run experiment with execution loop
        result = asyncio.run(
            run_cognitive_iteration_experiment(sentence, args.max_loops, args.question, args.local),
        )

        # Save results if requested
        if args.save_results and result:
            try:
                with open(f"{args.save_results}_{index:03d}.json", "w") as f:
                    to_save = {
                        "run": CURRENT_INDEX,
                        "topic": sentence,
                        "loops": LOOP_COUNT,
                        "result": result,
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
                    json.dump(to_save, f, indent=2, default=str)
                    print(f"✅ Results saved to {args.save_results}_{index:03d}")
            except Exception as e:
                print(f"❌ Failed to save results: {e}")

        print(f"\n📊 Experiment {index} completed with {LOOP_COUNT} loops")

    print(f"\n🎉 All {len(QUESTIONS)} experiments completed!")


if __name__ == "__main__":
    main()
