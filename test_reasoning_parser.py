#!/usr/bin/env python3
"""
Test script for reasoning model JSON parsing
"""

from orka.agents.llm_agents import parse_llm_json_response

# Test response from your trace file (reasoning model)
reasoning_response = """<think>
Alright, I need to help this user create a research document for analysis based on their query. Let me start by understanding exactly what they want.

The user provided an input which is a simple description of what it means to be an AI. They also have previous outputs that include some detailed responses and internal reasoning. My task is to clean and structure this into a markdown version, removing any formatting artifacts and standardizing the section headers.

Looking at their example response, they want a clear markdown document with specific sections like Task Description, Previous Outputs, Constraints, and Internal Reasoning. Each of these sections should be properly formatted with headers that are standardized, probably using bold for section titles and headers within.

I notice in their previous outputs, there's a 'previous_outputs' key which is an array containing another object. That's helpful because it shows multiple responses from different sources. I'll need to include both the user's input and the examples they provided, ensuring that each section flows logically.

In the Task Description, I should define AI concisely but comprehensively. The previous response already does this by explaining what AI is, its purpose, and some definitions like narrow vs. generative AI. That's a solid foundation. I'll make sure to include that here, keeping it clear and concise.

For the Previous Outputs section, I need to list each example with their respective responses and scores. The user provided two examples: answer_17 and duckduckgo_18. Each has a response, confidence score, and internal reasoning. I should format them under "previous_outputs" as sub-sections, but wait, the structure is 'prev outputs' which seems to include both the task and the previous outputs.
</think>

```markdown
{
    "task_description": {
        "response": "An AI is a system designed to perform tasks that typically require human intelligence. It can be broadly categorized into narrow AI (weak AI) and generative AI (strong AI). Narrow AI is designed for specific tasks, such as voice assistants or video games, while generative AI creates new content like text, images, or music.",
        "confidence": 0.9,
        "internal_reasoning": "The task description provides a concise and comprehensive overview of what an AI entails, covering its definitions, scopes, types, and applications."
    },
    "prev_outputs": [{
        "response": "What is artificial intelligence? Artificial intelligence (AI) is the theory and development of computer systems capable of performing tasks that historically required human intelligence, such as recognizing speech, making decisions, and identifying patterns. AI is an umbrella term that encompasses a wide variety of technologies, including machine learning, deep learning, and natural language processing.",
        "confidence": 0.9,
        "internal_reasoning": "A brief explanation of the basic concepts and scope of AI."
    }]
}
```"""

# Test response that should follow new format (with proper JSON)
improved_response = """```json
{
  "response": "An AI is a system designed to perform tasks that typically require human intelligence. It can be broadly categorized into narrow AI (weak AI) and generative AI (strong AI). Narrow AI is designed for specific tasks, such as voice assistants or video games, while generative AI creates new content like text, images, or music.",
  "confidence": "0.9",
  "internal_reasoning": "I approached this by first defining AI in simple terms, then categorizing it into narrow vs generative AI with clear examples to help users understand the different types and their applications."
}
```"""

# Test malformed JSON that needs fixing
malformed_response = """```json
{
  response: "This is missing quotes around keys",
  confidence: 0.8,
  internal_reasoning: "Testing the JSON fixer function"
}
```"""


def test_reasoning_parser():
    """Test the improved JSON parser with reasoning model responses"""
    print("🧠 Testing Reasoning Model JSON Parser")
    print("=" * 60)

    test_cases = [
        ("Reasoning model with <think> blocks", reasoning_response),
        ("Improved format (proper JSON)", improved_response),
        ("Malformed JSON (needs fixing)", malformed_response),
    ]

    for name, response in test_cases:
        print(f"\n📝 Test: {name}")
        print("-" * 40)

        # Show first part of input
        display_input = response.strip()[:150] + "..." if len(response) > 150 else response.strip()
        print(f"Input: {display_input}")

        # Parse the response
        result = parse_llm_json_response(response)

        print("\n✅ Parsed Result:")
        print(f"  📤 Response: {result.get('response', 'N/A')[:80]}...")
        print(f"  🎯 Confidence: {result.get('confidence', 'N/A')}")
        print(f"  🧩 Reasoning: {result.get('internal_reasoning', 'N/A')[:80]}...")

        print("\n" + "=" * 60)


def test_with_actual_trace():
    """Test with actual response from your trace file"""
    print("\n🔍 Testing with Actual Trace Data")
    print("=" * 60)

    # This is the actual problematic response from your trace
    actual_response = """<think>
Alright, I need to help this user create a research document for analysis based on their query. Let me start by understanding exactly what they want.

The user provided an input which is a simple description of what it means to be an AI. They also have previous outputs that include some detailed responses and internal reasoning. My task is to clean and structure this into a markdown version, removing any formatting artifacts and standardizing the section headers.

Looking at their example response, they want a clear markdown document with specific sections like Task Description, Previous Outputs, Constraints, and Internal Reasoning. Each of these sections should be properly formatted with headers that are standardized, probably using bold for section titles and headers within.

I notice in their previous outputs, there's a 'previous_outputs' key which is an array containing another object. That's helpful because it shows multiple responses from different sources. I'll need to include both the user's input and the examples they provided, ensuring that each section flows logically.

In the Task Description, I should define AI concisely but comprehensively. The previous response already does this by explaining what AI is, its purpose, and some definitions like narrow vs. generative AI. That's a solid foundation. I'll make sure to include that here, keeping it clear and concise.

For the Previous Outputs section, I need to list each example with their respective responses and scores. The user provided two examples: answer_17 and duckduckgo_18. Each has a response, confidence score, and internal reasoning. I should format them under "previous_outputs" as sub-sections, but wait, the structure is 'prev outputs' which seems to include both the task and the previous outputs.

Hmm, perhaps I misread that. In their initial query, they have a markdown example with a task description, then another section labeled 'previous_outputs'. Inside that, there are two bullet points each listing answer_17 and duckduckgo_18. Each of these has their response, confidence, and internal reasoning.

So, I need to structure the markdown accordingly: first the Task Description in a bolded section, followed by a header for "prev outputs", then under that, two bullet points each containing the details from answer_17 and duckduckgo_18. Each of these bullets will have their respective sections.

I should also make sure the headers are consistent—bold for main headers like Task Description, prev Outputs, etc.—and each section is properly indented with a hyphen. Also, the internal reasoning under each bullet needs to be concise but informative.

Let me outline the structure:

1. Task Description
   - Section 1: Definition of AI
      - Subsection: What does it mean? (definition)
      - Subsection: Definitions (narrow vs generative AI)
        - Subsection: Narrow AI (Weak AI)
          - Example: Video games, personal assistants
          - Response from answer_17
        - Subsection: Generative AI
          - Example: Creating text, images
          - Response from duckduckgo_18
   - Section 2: Scope and Application
      - Subsection: Types of AI (narrow vs generative)
      - Subsection: Applications across industries

Wait, the previous outputs have bullet points for each source. So under 'prev outputs', I should list both answer_17 and duckduckgo_18, each with their response, confidence score, and internal reasoning.

I think that's all the necessary sections. Now, putting it together in markdown format with headers and proper structure.

Let me double-check for any formatting issues. Each section starts with a bolded title, followed by an optional subtitle in parentheses if needed. The bullet points under 'prev outputs' should be correctly formatted with each point having its own sub-bullet sections.

I also need to ensure that the confidence scores are correctly placed under their respective responses and that internal reasoning is clear and concise for analysis.

Once I have all these elements, the markdown will be clean and well-structured as requested.
</think>

```markdown
{
    "task_description": {
        "response": "An AI is a system designed to perform tasks that typically require human intelligence. It can be broadly categorized into narrow AI (weak AI) and generative AI (strong AI). Narrow AI is designed for specific tasks, such as voice assistants or video games, while generative AI creates new content like text, images, or music.",
        "confidence": 0.9,
        "internal_reasoning": "The task description provides a concise and comprehensive overview of what an AI entails, covering its definitions, scopes, types, and applications."
    },
    "prev_outputs": [{
        "response": "What is artificial intelligence? Artificial intelligence (AI) is the theory and development of computer systems capable of performing tasks that historically required human intelligence, such as recognizing speech, making decisions, and identifying patterns. AI is an umbrella term that encompasses a wide variety of technologies, including machine learning, deep learning, and natural language processing.",
        "confidence": 0.9,
        "internal_reasoning": "A brief explanation of the basic concepts and scope of AI."
    }, [{
        "response": [
            {
                "response": "Generative AI, sometimes called 'gen AI', refers to deep learning models that can create complex original content such as long-form text, high-quality images, realistic video or audio and more in response to a user's prompt or request.",
                "confidence": 0.9,
                "internal_reasoning": "An explanation of generative AI, focusing on its capabilities and applications."
            },
            {
                "response": "Narrow AI: Also known as weak AI, this system is designed to carry out one particular job. Weak AI systems include video games and personal assistants like Amazon's Alexa and Apple's Siri.",
                "confidence": 0.9,
                "internal_reasoning": "A detailed explanation of narrow AI, highlighting its limitations."
            }
        ]
    }]
}
```"""

    print("📝 Parsing actual problematic response from trace...")
    result = parse_llm_json_response(actual_response)

    print("\n✅ Successfully parsed! Results:")
    print(f"  📤 Response: {result.get('response', 'N/A')[:100]}...")
    print(f"  🎯 Confidence: {result.get('confidence', 'N/A')}")
    print(f"  🧩 Internal Reasoning: {result.get('internal_reasoning', 'N/A')[:100]}...")

    # Check if reasoning was extracted from <think> blocks
    reasoning = result.get("internal_reasoning", "")
    if "Reasoning:" in reasoning:
        print("\n🧠 Extracted reasoning from <think> blocks!")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_reasoning_parser()
    test_with_actual_trace()

    print("\n🎉 All tests completed!")
    print("\n💡 Usage Tips:")
    print("1. The parser now handles <think> blocks from reasoning models")
    print("2. It extracts JSON from markdown code blocks")
    print("3. It attempts to fix malformed JSON")
    print("4. It always returns a structured dict with response, confidence, internal_reasoning")
    print("5. Use this in your LocalLLMAgent for consistent output formatting")
