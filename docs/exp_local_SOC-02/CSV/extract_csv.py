#!/usr/bin/env python3
"""
Society of Mind Orka Data Extractor
Extracts reasoning, self-awareness, and cognitive process metrics from JSON log files.
Focuses on Society of Mind analysis for deepseek-r1:32b model execution.
"""

import ast
import csv
import json
import re


class SocietyOfMindExtractor:
    def __init__(self, file_paths: list[str]):
        self.file_paths = file_paths
        self.data = []
        self.reasoning_indicators = [
            "reasoning",
            "analysis",
            "logic",
            "inference",
            "deduction",
            "conclusion",
            "because",
            "therefore",
            "hence",
            "thus",
            "consequently",
            "leads to",
            "evidence",
            "support",
            "justification",
            "rationale",
            "explanation",
        ]
        self.self_awareness_indicators = [
            "I am",
            "I think",
            "I believe",
            "I understand",
            "I realize",
            "I know",
            "my perspective",
            "my view",
            "my understanding",
            "my experience",
            "myself",
            "self-reflection",
            "introspection",
            "self-analysis",
            "awareness",
            "consciousness",
            "self-aware",
            "meta-cognitive",
        ]
        self.cognitive_indicators = [
            "memory",
            "remember",
            "recall",
            "learn",
            "understand",
            "comprehend",
            "process",
            "think",
            "analyze",
            "evaluate",
            "judge",
            "decide",
            "cognitive",
            "mental",
            "intellectual",
            "conceptual",
            "abstract",
            "pattern",
            "connection",
            "association",
            "synthesis",
            "integration",
        ]

    def load_data(self):
        """Load all JSON files"""
        for file_path in self.file_paths:
            try:
                with open(file_path, encoding="utf-8") as f:
                    data = json.load(f)
                    self.data.append(
                        {
                            "file_path": file_path,
                            "data": data,
                            "metadata": data.get("_metadata", {}),
                        },
                    )
                    print(f"Loaded {file_path}")
            except Exception as e:
                print(f"Error loading {file_path}: {e}")

    def safe_eval(self, response_str: str) -> dict:
        """Safely evaluate response strings"""
        try:
            if response_str.startswith("{") and response_str.endswith("}"):
                try:
                    return json.loads(response_str)
                except json.JSONDecodeError:
                    try:
                        return ast.literal_eval(response_str)
                    except (ValueError, SyntaxError):
                        try:
                            return eval(response_str)
                        except:
                            return {}
            return {}
        except Exception:
            return {}

    def calculate_indicator_percentage(self, text: str, indicators: list[str]) -> float:
        """Calculate percentage of indicators found in text"""
        if not text:
            return 0.0

        text_lower = text.lower()
        found_indicators = 0
        total_words = len(text.split())

        for indicator in indicators:
            if indicator in text_lower:
                found_indicators += text_lower.count(indicator)

        # Calculate percentage based on indicator density
        if total_words > 0:
            return min(100.0, (found_indicators / total_words) * 100 * 10)  # Scaled for readability
        return 0.0

    def extract_reasoning_analysis(self):
        """Extract reasoning process evidence"""
        reasoning_data = []

        for file_info in self.data:
            file_path = file_info["file_path"]
            data = file_info["data"]

            timestamp_match = re.search(r"(\d{8}_\d{6})", file_path)
            timestamp = timestamp_match.group(1) if timestamp_match else "unknown"

            blob_store = data.get("blob_store", {})

            for blob_key, blob_data in blob_store.items():
                # Extract response text
                response_text = ""
                if "result" in blob_data and "response" in blob_data["result"]:
                    response_text = blob_data["result"]["response"]

                # Extract prompt text
                prompt_text = blob_data.get("formatted_prompt", "")

                # Combined text for analysis
                combined_text = f"{prompt_text} {response_text}"

                # Calculate reasoning percentage
                reasoning_percentage = self.calculate_indicator_percentage(
                    combined_text,
                    self.reasoning_indicators,
                )

                # Extract specific reasoning patterns
                reasoning_patterns = []
                for indicator in self.reasoning_indicators:
                    if indicator in combined_text.lower():
                        reasoning_patterns.append(indicator)

                loop_number = self._extract_loop_number(blob_data)
                agent_type = self._extract_agent_type(blob_data)

                reasoning_row = {
                    "file_path": file_path,
                    "timestamp": timestamp,
                    "loop_number": loop_number,
                    "agent_type": agent_type,
                    "blob_key": blob_key,
                    "reasoning_percentage": reasoning_percentage,
                    "reasoning_patterns": " | ".join(reasoning_patterns),
                    "text_length": len(combined_text),
                    "response_length": len(response_text),
                    "prompt_length": len(prompt_text),
                    "has_logical_structure": any(
                        word in combined_text.lower()
                        for word in ["therefore", "because", "thus", "hence"]
                    ),
                    "has_evidence": any(
                        word in combined_text.lower() for word in ["evidence", "support", "proof"]
                    ),
                    "has_analysis": any(
                        word in combined_text.lower() for word in ["analysis", "analyze", "examine"]
                    ),
                }
                reasoning_data.append(reasoning_row)

        return reasoning_data

    def extract_self_awareness_analysis(self):
        """Extract self-awareness evidence"""
        awareness_data = []

        for file_info in self.data:
            file_path = file_info["file_path"]
            data = file_info["data"]

            timestamp_match = re.search(r"(\d{8}_\d{6})", file_path)
            timestamp = timestamp_match.group(1) if timestamp_match else "unknown"

            blob_store = data.get("blob_store", {})

            for blob_key, blob_data in blob_store.items():
                response_text = ""
                if "result" in blob_data and "response" in blob_data["result"]:
                    response_text = blob_data["result"]["response"]

                prompt_text = blob_data.get("formatted_prompt", "")
                combined_text = f"{prompt_text} {response_text}"

                # Calculate self-awareness percentage
                awareness_percentage = self.calculate_indicator_percentage(
                    combined_text,
                    self.self_awareness_indicators,
                )

                # Extract specific self-awareness patterns
                awareness_patterns = []
                for indicator in self.self_awareness_indicators:
                    if indicator in combined_text.lower():
                        awareness_patterns.append(indicator)

                loop_number = self._extract_loop_number(blob_data)
                agent_type = self._extract_agent_type(blob_data)

                awareness_row = {
                    "file_path": file_path,
                    "timestamp": timestamp,
                    "loop_number": loop_number,
                    "agent_type": agent_type,
                    "blob_key": blob_key,
                    "awareness_percentage": awareness_percentage,
                    "awareness_patterns": " | ".join(awareness_patterns),
                    "first_person_usage": combined_text.lower().count("i "),
                    "self_reference": combined_text.lower().count("my ")
                    + combined_text.lower().count("myself"),
                    "meta_cognitive": any(
                        word in combined_text.lower()
                        for word in ["meta", "self-reflection", "introspection"]
                    ),
                    "experiential": any(
                        word in combined_text.lower() for word in ["experience", "feel", "sense"]
                    ),
                }
                awareness_data.append(awareness_row)

        return awareness_data

    def extract_cognitive_analysis(self):
        """Extract cognitive process evidence"""
        cognitive_data = []

        for file_info in self.data:
            file_path = file_info["file_path"]
            data = file_info["data"]

            timestamp_match = re.search(r"(\d{8}_\d{6})", file_path)
            timestamp = timestamp_match.group(1) if timestamp_match else "unknown"

            blob_store = data.get("blob_store", {})

            for blob_key, blob_data in blob_store.items():
                response_text = ""
                if "result" in blob_data and "response" in blob_data["result"]:
                    response_text = blob_data["result"]["response"]

                prompt_text = blob_data.get("formatted_prompt", "")
                combined_text = f"{prompt_text} {response_text}"

                # Calculate cognitive percentage
                cognitive_percentage = self.calculate_indicator_percentage(
                    combined_text,
                    self.cognitive_indicators,
                )

                # Extract specific cognitive patterns
                cognitive_patterns = []
                for indicator in self.cognitive_indicators:
                    if indicator in combined_text.lower():
                        cognitive_patterns.append(indicator)

                loop_number = self._extract_loop_number(blob_data)
                agent_type = self._extract_agent_type(blob_data)

                cognitive_row = {
                    "file_path": file_path,
                    "timestamp": timestamp,
                    "loop_number": loop_number,
                    "agent_type": agent_type,
                    "blob_key": blob_key,
                    "cognitive_percentage": cognitive_percentage,
                    "cognitive_patterns": " | ".join(cognitive_patterns),
                    "memory_references": combined_text.lower().count("memory")
                    + combined_text.lower().count("remember"),
                    "processing_terms": combined_text.lower().count("process")
                    + combined_text.lower().count("analyze"),
                    "learning_terms": combined_text.lower().count("learn")
                    + combined_text.lower().count("understand"),
                    "pattern_recognition": any(
                        word in combined_text.lower()
                        for word in ["pattern", "connection", "association"]
                    ),
                    "abstract_thinking": any(
                        word in combined_text.lower()
                        for word in ["abstract", "conceptual", "theoretical"]
                    ),
                }
                cognitive_data.append(cognitive_row)

        return cognitive_data

    def analyze_memory_vs_past_loops(self):
        """Analyze relevance of memory vs past_loops data"""
        memory_analysis = []

        for file_info in self.data:
            file_path = file_info["file_path"]
            data = file_info["data"]

            timestamp_match = re.search(r"(\d{8}_\d{6})", file_path)
            timestamp = timestamp_match.group(1) if timestamp_match else "unknown"

            blob_store = data.get("blob_store", {})

            for blob_key, blob_data in blob_store.items():
                # Check for memory data
                memory_data = blob_data.get("result", {}).get("memories", [])
                memory_count = len(memory_data) if memory_data else 0

                # Check for past_loops data
                input_data = blob_data.get("input", {})
                if isinstance(input_data, dict):
                    past_loops_data = input_data.get("past_loops", [])
                else:
                    past_loops_data = []
                past_loops_count = len(past_loops_data) if past_loops_data else 0

                # Analyze memory content
                memory_content_length = 0
                memory_relevance_score = 0
                if memory_data:
                    for memory in memory_data:
                        content = str(memory.get("content", ""))
                        memory_content_length += len(content)
                        # Simple relevance scoring based on content richness
                        if content:
                            memory_relevance_score += min(10, len(content.split()) / 10)

                # Analyze past_loops content
                past_loops_content_length = 0
                past_loops_relevance_score = 0
                if past_loops_data:
                    for loop in past_loops_data:
                        content = str(loop)
                        past_loops_content_length += len(content)
                        # Simple relevance scoring
                        if content:
                            past_loops_relevance_score += min(10, len(content.split()) / 10)

                loop_number = self._extract_loop_number(blob_data)
                agent_type = self._extract_agent_type(blob_data)

                memory_row = {
                    "file_path": file_path,
                    "timestamp": timestamp,
                    "loop_number": loop_number,
                    "agent_type": agent_type,
                    "blob_key": blob_key,
                    "memory_count": memory_count,
                    "past_loops_count": past_loops_count,
                    "memory_content_length": memory_content_length,
                    "past_loops_content_length": past_loops_content_length,
                    "memory_relevance_score": memory_relevance_score,
                    "past_loops_relevance_score": past_loops_relevance_score,
                    "memory_vs_past_loops_ratio": (
                        memory_relevance_score / max(1, past_loops_relevance_score)
                    ),
                    "primary_data_source": "memory"
                    if memory_relevance_score > past_loops_relevance_score
                    else "past_loops",
                    "data_richness": "high"
                    if (memory_content_length + past_loops_content_length) > 1000
                    else "low",
                }
                memory_analysis.append(memory_row)

        return memory_analysis

    def _extract_agent_type(self, blob_data) -> str:
        """Extract agent type from blob data"""
        # Check multiple locations for agent type
        locations = [
            ("result", "metadata", "agent_type"),
            ("input", "metadata", "agent_type"),
            ("result", "memories", 0, "metadata", "agent_type"),
        ]

        for location in locations:
            try:
                current = blob_data
                for key in location:
                    if isinstance(key, int):
                        current = (
                            current[key]
                            if isinstance(current, list) and len(current) > key
                            else None
                        )
                    else:
                        current = current.get(key) if isinstance(current, dict) else None
                    if current is None:
                        break
                if current:
                    return current
            except (KeyError, IndexError, TypeError):
                continue

        # Check formatted_prompt for hints
        if "formatted_prompt" in blob_data:
            prompt = blob_data["formatted_prompt"].lower()
            if "progressive" in prompt:
                return "progressive"
            elif "conservative" in prompt:
                return "conservative"
            elif "realist" in prompt:
                return "realist"
            elif "purist" in prompt:
                return "purist"
            elif "advocate" in prompt:
                return "devils_advocate"
            elif "moderator" in prompt:
                return "moderator"

        return "unknown"

    def _extract_loop_number(self, blob_data) -> int:
        """Extract loop number from blob data"""
        locations = [
            ("input", "loop_number"),
            ("result", "metadata", "loop_number"),
            ("result", "memories", 0, "metadata", "loop_number"),
        ]

        for location in locations:
            try:
                current = blob_data
                for key in location:
                    if isinstance(key, int):
                        current = (
                            current[key]
                            if isinstance(current, list) and len(current) > key
                            else None
                        )
                    else:
                        current = current.get(key) if isinstance(current, dict) else None
                    if current is None:
                        break
                if current is not None:
                    return int(current)
            except (KeyError, IndexError, TypeError, ValueError):
                continue

        return 0

    def save_to_csv(self, data: list[dict], filename: str):
        """Save data to CSV file"""
        if not data:
            print(f"No data to save for {filename}")
            return

        with open(filename, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)

        print(f"Saved {len(data)} rows to {filename}")

    def generate_summary_report(self, reasoning_data, awareness_data, cognitive_data, memory_data):
        """Generate summary report with percentages"""
        print("\n" + "=" * 60)
        print("SOCIETY OF MIND ANALYSIS SUMMARY")
        print("=" * 60)

        # Calculate overall percentages
        total_entries = len(reasoning_data)

        if total_entries > 0:
            avg_reasoning = (
                sum(row["reasoning_percentage"] for row in reasoning_data) / total_entries
            )
            avg_awareness = (
                sum(row["awareness_percentage"] for row in awareness_data) / total_entries
            )
            avg_cognitive = (
                sum(row["cognitive_percentage"] for row in cognitive_data) / total_entries
            )

            print(f"Total entries analyzed: {total_entries}")
            print(f"Average reasoning evidence: {avg_reasoning:.1f}%")
            print(f"Average self-awareness evidence: {avg_awareness:.1f}%")
            print(f"Average cognitive process evidence: {avg_cognitive:.1f}%")

            # Memory vs past_loops analysis
            memory_primary = sum(1 for row in memory_data if row["primary_data_source"] == "memory")
            past_loops_primary = sum(
                1 for row in memory_data if row["primary_data_source"] == "past_loops"
            )

            print("\nMemory vs Past Loops Relevance:")
            print(
                f"Memory more relevant: {memory_primary} cases ({memory_primary / total_entries * 100:.1f}%)",
            )
            print(
                f"Past loops more relevant: {past_loops_primary} cases ({past_loops_primary / total_entries * 100:.1f}%)",
            )

            # Agent type analysis
            agent_types = {}
            for row in reasoning_data:
                agent_type = row["agent_type"]
                if agent_type not in agent_types:
                    agent_types[agent_type] = {
                        "count": 0,
                        "reasoning": 0,
                        "awareness": 0,
                        "cognitive": 0,
                    }
                agent_types[agent_type]["count"] += 1
                agent_types[agent_type]["reasoning"] += row["reasoning_percentage"]

            for awareness_row in awareness_data:
                agent_type = awareness_row["agent_type"]
                if agent_type in agent_types:
                    agent_types[agent_type]["awareness"] += awareness_row["awareness_percentage"]

            for cognitive_row in cognitive_data:
                agent_type = cognitive_row["agent_type"]
                if agent_type in agent_types:
                    agent_types[agent_type]["cognitive"] += cognitive_row["cognitive_percentage"]

            print("\nAgent Type Analysis:")
            for agent_type, stats in agent_types.items():
                if stats["count"] > 0:
                    print(
                        f"{agent_type}: R={stats['reasoning'] / stats['count']:.1f}% "
                        f"A={stats['awareness'] / stats['count']:.1f}% "
                        f"C={stats['cognitive'] / stats['count']:.1f}% ({stats['count']} entries)",
                    )

        print("=" * 60)

    def extract_all_society_data(self):
        """Extract all Society of Mind data"""
        print("Loading data...")
        self.load_data()

        print("Extracting reasoning process analysis...")
        reasoning_data = self.extract_reasoning_analysis()
        self.save_to_csv(reasoning_data, "society_reasoning_analysis.csv")

        print("Extracting self-awareness analysis...")
        awareness_data = self.extract_self_awareness_analysis()
        self.save_to_csv(awareness_data, "society_awareness_analysis.csv")

        print("Extracting cognitive process analysis...")
        cognitive_data = self.extract_cognitive_analysis()
        self.save_to_csv(cognitive_data, "society_cognitive_analysis.csv")

        print("Analyzing memory vs past_loops relevance...")
        memory_data = self.analyze_memory_vs_past_loops()
        self.save_to_csv(memory_data, "society_memory_analysis.csv")

        print("Generating summary report...")
        self.generate_summary_report(reasoning_data, awareness_data, cognitive_data, memory_data)

        print("Society of Mind analysis complete!")


def main():
    # Define your specific file paths
    file_paths = [
        "orka_trace_20250713_143008.json",
        "orka_trace_20250713_143345.json",
        "orka_trace_20250713_143718.json",
        "orka_trace_20250713_144045.json",
        "orka_trace_20250713_144407.json",
        "orka_trace_20250713_144729.json",
        "orka_trace_20250713_145104.json",
        "orka_trace_20250713_145433.json",
        "orka_trace_20250713_145752.json",
        "orka_trace_20250713_150128.json",
        "orka_trace_20250713_150221.json",
    ]

    # Create extractor and run Society of Mind analysis
    extractor = SocietyOfMindExtractor(file_paths)
    extractor.extract_all_society_data()


if __name__ == "__main__":
    main()
