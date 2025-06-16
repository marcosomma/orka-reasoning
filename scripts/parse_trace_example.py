#!/usr/bin/env python3
"""
Example script to parse LLM responses from trace files
"""

import json

from orka.agents.llm_agents import parse_llm_json_response


def parse_trace_llm_responses(trace_file_path):
    """
    Parse LLM responses from a trace file and extract structured JSON data

    Args:
        trace_file_path (str): Path to the trace JSON file

    Returns:
        list: List of parsed agent responses with structured data
    """
    parsed_responses = []

    try:
        with open(trace_file_path, encoding="utf-8") as f:
            trace_data = json.load(f)

        for entry in trace_data:
            if entry.get("event_type") in [
                "OpenAIAnswerBuilder",
                "ForkedAgent-OpenAIAnswerBuilder",
                "ForkedAgent-LocalLLMAgent",
            ]:
                payload = entry.get("payload", {})
                raw_result = payload.get("result", "")

                # Parse the LLM response
                parsed_json = parse_llm_json_response(raw_result)

                parsed_response = {
                    "agent_id": entry.get("agent_id"),
                    "event_type": entry.get("event_type"),
                    "timestamp": entry.get("timestamp"),
                    "step": entry.get("step"),
                    "raw_result": raw_result,
                    "parsed_data": parsed_json,
                    "parsing_success": parsed_json is not None,
                }

                parsed_responses.append(parsed_response)

    except Exception as e:
        print(f"Error parsing trace file: {e}")
        return []

    return parsed_responses


def analyze_llm_responses(trace_file_path):
    """Analyze and display parsed LLM responses"""
    print(f"Analyzing LLM responses from: {trace_file_path}\n")

    parsed_responses = parse_trace_llm_responses(trace_file_path)

    if not parsed_responses:
        print("No LLM responses found or parsing failed.")
        return

    print(f"Found {len(parsed_responses)} LLM responses:")
    print("=" * 80)

    for i, response in enumerate(parsed_responses, 1):
        print(f"\n{i}. Agent: {response['agent_id']} ({response['event_type']})")
        print(f"   Step: {response['step']}")
        print(f"   Parsing: {'✅ Success' if response['parsing_success'] else '❌ Failed'}")

        if response["parsed_data"]:
            data = response["parsed_data"]
            print(f"   Response: {data.get('response', 'N/A')[:80]}...")
            print(f"   Confidence: {data.get('confidence', 'N/A')}")
            print(f"   Reasoning: {data.get('internal_reasoning', 'N/A')[:60]}...")
        else:
            print(f"   Raw result (first 100 chars): {response['raw_result'][:100]}...")

        print("-" * 80)


def extract_agent_responses_as_dict(trace_file_path):
    """
    Extract agent responses as a clean dictionary for further processing

    Returns:
        dict: Agent ID -> parsed response data
    """
    parsed_responses = parse_trace_llm_responses(trace_file_path)

    result = {}
    for response in parsed_responses:
        if response["parsing_success"] and response["parsed_data"]:
            result[response["agent_id"]] = response["parsed_data"]

    return result


if __name__ == "__main__":
    # Example usage with your trace file
    trace_file = "logs/orka_trace_20250608_094338.json"

    print("1. Analyzing LLM responses:")
    analyze_llm_responses(trace_file)

    print("\n" + "=" * 80)
    print("2. Extracting responses as dictionary:")
    agent_responses = extract_agent_responses_as_dict(trace_file)

    for agent_id, data in agent_responses.items():
        print(f"\n{agent_id}:")
        print(f"  Response: {data.get('response', 'N/A')}")
        print(f"  Confidence: {data.get('confidence', 'N/A')}")
        print(f"  Reasoning: {data.get('internal_reasoning', 'N/A')}")
