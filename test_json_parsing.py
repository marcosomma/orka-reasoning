#!/usr/bin/env python3
"""
Test script to demonstrate JSON parsing from LLM responses
"""

from orka.agents.llm_agents import parse_llm_json_response

# Test cases from your trace file
test_responses = [
    # Good JSON response
    """```json
{ 
  "response": "What does it mean to be an AI?", 
  "confidence": "0.9", 
  "internal_reasoning": "The search sentence clearly reflects the user's request to describe the concept of being an AI." 
}
```""",
    # JSON with missing commas (like from local LLM)
    """```json
{
  "response": "An AI, short for artificial intelligence, is a machine designed to mimic human-like thought processes."

  "confidence": "0.9"

  "internal_reasoning": "The description focuses on machines mimicking human-like thinking and behavior."
}
```""",
    # JSON with <think> blocks
    """<think>
This is internal reasoning...
</think>

```json
{
  "response": "AI refers to artificial intelligence systems.",
  "confidence": "0.8",
  "internal_reasoning": "Simple definition of AI concept."
}
```""",
    # Malformed JSON
    """```json
{
  response: "This has unquoted keys",
  confidence: 0.7,
  internal_reasoning: "Testing malformed JSON"
}
```""",
]


def test_json_parsing():
    """Test the JSON parsing function with various response formats"""
    print("Testing JSON parsing functionality:\n")

    for i, response in enumerate(test_responses, 1):
        print(f"Test {i}:")
        print("Input:")
        print(response[:100] + "..." if len(response) > 100 else response)
        print("\nParsed result:")

        result = parse_llm_json_response(response)
        if result:
            print("✅ Success!")
            print(f"  Response: {result.get('response', 'N/A')[:50]}...")
            print(f"  Confidence: {result.get('confidence', 'N/A')}")
            print(f"  Reasoning: {result.get('internal_reasoning', 'N/A')[:50]}...")
        else:
            print("❌ Failed to parse")

        print("-" * 60)


if __name__ == "__main__":
    test_json_parsing()
