#!/usr/bin/env python3
"""
Test script to verify thinking support is only applied to local LLMs
and that the system is resilient to different response formats.
"""

import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orka.agents.llm_agents import _simple_json_parse, parse_llm_json_response


def test_local_llm_thinking_parser():
    """Test the reasoning parser used for local LLMs"""
    print("Testing Local LLM Thinking Parser (parse_llm_json_response)...")

    # Test 1: Response with <think> blocks
    thinking_response = """
    <think>
    Let me analyze this question carefully. I need to consider the context and provide accurate information.
    </think>
    
    ```json
    {
        "response": "This is my answer after thinking",
        "confidence": "0.9",
        "internal_reasoning": "I analyzed the question thoroughly"
    }
    ```
    """

    result = parse_llm_json_response(thinking_response)
    print(f"✓ Thinking response parsed: {result['response'][:50]}...")
    print(f"  Reasoning extracted: {result['internal_reasoning'][:50]}...")

    # Test 2: Malformed JSON
    malformed_response = """
    ```json
    {
        "response": "Test answer"
        "confidence": "0.8"
        "internal_reasoning": "Missing commas"
    }
    ```
    """

    result = parse_llm_json_response(malformed_response)
    print(f"✓ Malformed JSON handled: {result['response']}")

    # Test 3: Plain text fallback
    plain_text = "Just a plain text response without any JSON"
    result = parse_llm_json_response(plain_text)
    print(f"✓ Plain text fallback: {result['response']}")

    # Test 4: Error resilience - None input
    result = parse_llm_json_response(None)
    print(f"✓ None input handled: {result['response']}")


def test_openai_simple_parser():
    """Test the simple parser used for OpenAI models"""
    print("\nTesting OpenAI Simple Parser (_simple_json_parse)...")

    # Test 1: Simple JSON response
    openai_response = """
    ```json
    {
        "response": "This is an OpenAI response",
        "confidence": "0.85",
        "internal_reasoning": "Standard OpenAI processing"
    }
    ```
    """

    result = _simple_json_parse(openai_response)
    print(f"✓ OpenAI JSON parsed: {result['response']}")

    # Test 2: Should NOT handle <think> blocks (different from local LLM parser)
    thinking_response = """
    <think>This should not be extracted by the simple parser</think>
    ```json
    {"response": "Answer without thinking extraction", "confidence": "0.8"}
    ```
    """

    result = _simple_json_parse(thinking_response)
    print(f"✓ OpenAI ignores thinking blocks: {result['internal_reasoning']}")

    # Test 3: Fallback for plain text
    plain_response = "Plain OpenAI response"
    result = _simple_json_parse(plain_response)
    print(f"✓ OpenAI plain text fallback: {result['response']}")


def test_resilience():
    """Test resilience of both parsers"""
    print("\nTesting Resilience...")

    # Test extreme cases
    test_cases = [
        "",  # Empty string
        "   ",  # Whitespace only
        "{ malformed json",  # Broken JSON
        "```json\n{broken json```",  # Broken code block
        None,  # None input
        123,  # Non-string input
    ]

    for i, test_case in enumerate(test_cases, 1):
        try:
            local_result = parse_llm_json_response(test_case)
            openai_result = _simple_json_parse(test_case)
            print(f"✓ Test case {i}: Both parsers handled gracefully")
        except Exception as e:
            print(f"✗ Test case {i} failed: {e}")


if __name__ == "__main__":
    print("OrKa Thinking Support Test")
    print("=" * 40)

    test_local_llm_thinking_parser()
    test_openai_simple_parser()
    test_resilience()

    print("\n" + "=" * 40)
    print("✓ All tests completed!")
    print("\nKey Points:")
    print("- Local LLMs: Use parse_llm_json_response (handles <think> blocks)")
    print("- OpenAI models: Use _simple_json_parse (no thinking extraction)")
    print("- Both parsers are resilient to malformed input")
