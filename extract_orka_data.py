#!/usr/bin/env python3
"""
Extract data from Orka trace files and convert to CSV format for analysis.
All data is extracted at agent granular level across loops.
"""

import csv
import json
import re
from collections import defaultdict

# Define agent types for consistency
AGENT_TYPES = [
    "radical_progressive",
    "traditional_conservative",
    "pragmatic_realist",
    "ethical_purist",
    "devils_advocate",
    "neutral_moderator",
]


class OrkaDataExtractor:
    def __init__(self, file_paths: list[str]):
        self.file_paths = file_paths
        self.data = []
        self.agent_data = defaultdict(list)
        self.loop_data = defaultdict(list)
        self.convergence_data = []
        self.quality_data = []
        self.cost_data = []
        self.token_data = []

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
                        }
                    )
                    print(f"Loaded {file_path}")
            except Exception as e:
                print(f"Error loading {file_path}: {e}")

    def extract_agent_position_data(self):
        """Extract OPENING_POSITION, CORE_*, CONSENSUS_PROPOSALS, CONVERGENCE_LEADERSHIP data"""
        position_data = []

        for file_info in self.data:
            file_path = file_info["file_path"]
            data = file_info["data"]

            # Extract timestamp from filename
            timestamp_match = re.search(r"(\d{8}_\d{6})", file_path)
            timestamp = timestamp_match.group(1) if timestamp_match else "unknown"

            # Process blob store for agent responses
            blob_store = data.get("blob_store", {})
            for blob_key, blob_data in blob_store.items():
                if "result" in blob_data and "response" in blob_data["result"]:
                    response_str = blob_data["result"]["response"]

                    # Parse response string if it's JSON-like
                    try:
                        if response_str.startswith("{") and response_str.endswith("}"):
                            response_data = eval(response_str)  # Using eval for JSON-like strings

                            # Extract agent info from metadata or other fields
                            agent_type = self._extract_agent_type(blob_data)
                            loop_number = self._extract_loop_number(blob_data)

                            # Extract metrics
                            metrics = blob_data["result"].get("_metrics", {})

                            position_row = {
                                "file_path": file_path,
                                "timestamp": timestamp,
                                "loop_number": loop_number,
                                "agent_type": agent_type,
                                "blob_key": blob_key,
                                "opening_position": response_data.get("OPENING_POSITION", ""),
                                "core_arguments": self._extract_list_field(
                                    response_data, "CORE_ARGUMENTS"
                                ),
                                "core_principles": self._extract_list_field(
                                    response_data, "CORE_PRINCIPLES"
                                ),
                                "consensus_proposals": self._extract_list_field(
                                    response_data, "CONSENSUS_PROPOSALS"
                                ),
                                "convergence_leadership": response_data.get(
                                    "CONVERGENCE_LEADERSHIP", ""
                                ),
                                "convergence_opportunities": self._extract_list_field(
                                    response_data, "CONVERGENCE_OPPORTUNITIES"
                                ),
                                "collaborative_proposals": self._extract_list_field(
                                    response_data, "COLLABORATIVE_PROPOSALS"
                                ),
                                "tokens": metrics.get("tokens", 0),
                                "cost_usd": metrics.get("cost_usd", 0.0),
                                "latency_ms": metrics.get("latency_ms", 0),
                                "model": metrics.get("model", ""),
                            }
                            position_data.append(position_row)

                    except Exception:
                        continue

        return position_data

    def extract_attack_defense_data(self):
        """Extract ATTACK_DEFLECTION, COUNTEROFFENSIVE, POSITION_REINFORCEMENT, MORAL_HIGH_GROUND data"""
        defense_data = []

        for file_info in self.data:
            file_path = file_info["file_path"]
            data = file_info["data"]

            timestamp_match = re.search(r"(\d{8}_\d{6})", file_path)
            timestamp = timestamp_match.group(1) if timestamp_match else "unknown"

            blob_store = data.get("blob_store", {})
            for blob_key, blob_data in blob_store.items():
                if "result" in blob_data and "response" in blob_data["result"]:
                    response_str = blob_data["result"]["response"]

                    try:
                        if response_str.startswith("{") and response_str.endswith("}"):
                            response_data = eval(response_str)

                            # Check if this response contains defense/attack data
                            if any(
                                key in response_data
                                for key in [
                                    "ATTACK_DEFLECTION",
                                    "COUNTEROFFENSIVE",
                                    "POSITION_REINFORCEMENT",
                                    "MORAL_HIGH_GROUND",
                                ]
                            ):
                                agent_type = self._extract_agent_type(blob_data)
                                loop_number = self._extract_loop_number(blob_data)
                                metrics = blob_data["result"].get("_metrics", {})

                                defense_row = {
                                    "file_path": file_path,
                                    "timestamp": timestamp,
                                    "loop_number": loop_number,
                                    "agent_type": agent_type,
                                    "blob_key": blob_key,
                                    "attack_deflection": response_data.get("ATTACK_DEFLECTION", ""),
                                    "counteroffensive": response_data.get("COUNTEROFFENSIVE", ""),
                                    "position_reinforcement": response_data.get(
                                        "POSITION_REINFORCEMENT", ""
                                    ),
                                    "moral_high_ground": response_data.get("MORAL_HIGH_GROUND", ""),
                                    "wisdom_superiority": response_data.get(
                                        "WISDOM_SUPERIORITY", ""
                                    ),
                                    "tokens": metrics.get("tokens", 0),
                                    "cost_usd": metrics.get("cost_usd", 0.0),
                                    "latency_ms": metrics.get("latency_ms", 0),
                                    "model": metrics.get("model", ""),
                                }
                                defense_data.append(defense_row)

                    except Exception:
                        continue

        return defense_data

    def extract_reasoning_quality_data(self):
        """Extract REASONING_QUALITY, QUALITY_ANALYSIS, PRODUCTIVE_DISAGREEMENTS at loop level"""
        quality_data = []

        for file_info in self.data:
            file_path = file_info["file_path"]
            data = file_info["data"]

            timestamp_match = re.search(r"(\d{8}_\d{6})", file_path)
            timestamp = timestamp_match.group(1) if timestamp_match else "unknown"

            blob_store = data.get("blob_store", {})
            for blob_key, blob_data in blob_store.items():
                if "result" in blob_data and "response" in blob_data["result"]:
                    response_str = blob_data["result"]["response"]

                    try:
                        if response_str.startswith("{") and response_str.endswith("}"):
                            response_data = eval(response_str)

                            # Check for quality metrics
                            if any(
                                key in response_data
                                for key in [
                                    "REASONING_QUALITY",
                                    "QUALITY_ANALYSIS",
                                    "PRODUCTIVE_DISAGREEMENTS",
                                ]
                            ):
                                loop_number = self._extract_loop_number(blob_data)
                                metrics = blob_data["result"].get("_metrics", {})

                                quality_row = {
                                    "file_path": file_path,
                                    "timestamp": timestamp,
                                    "loop_number": loop_number,
                                    "blob_key": blob_key,
                                    "reasoning_quality": response_data.get("REASONING_QUALITY", ""),
                                    "quality_analysis": response_data.get("QUALITY_ANALYSIS", ""),
                                    "productive_disagreements": response_data.get(
                                        "PRODUCTIVE_DISAGREEMENTS", ""
                                    ),
                                    "tokens": metrics.get("tokens", 0),
                                    "cost_usd": metrics.get("cost_usd", 0.0),
                                    "latency_ms": metrics.get("latency_ms", 0),
                                }
                                quality_data.append(quality_row)

                    except Exception:
                        continue

        return quality_data

    def extract_convergence_data(self):
        """Extract AGREEMENT_SCORE, CONVERGENCE_MOMENTUM, CONVERGENCE_TREND at loop level"""
        convergence_data = []

        for file_info in self.data:
            file_path = file_info["file_path"]
            data = file_info["data"]

            timestamp_match = re.search(r"(\d{8}_\d{6})", file_path)
            timestamp = timestamp_match.group(1) if timestamp_match else "unknown"

            blob_store = data.get("blob_store", {})
            for blob_key, blob_data in blob_store.items():
                if "result" in blob_data and "response" in blob_data["result"]:
                    response_str = blob_data["result"]["response"]

                    try:
                        if response_str.startswith("{") and response_str.endswith("}"):
                            response_data = eval(response_str)

                            # Check for convergence metrics
                            if any(
                                key in response_data
                                for key in [
                                    "AGREEMENT_SCORE",
                                    "CONVERGENCE_MOMENTUM",
                                    "CONVERGENCE_TREND",
                                ]
                            ):
                                loop_number = self._extract_loop_number(blob_data)
                                metrics = blob_data["result"].get("_metrics", {})

                                convergence_row = {
                                    "file_path": file_path,
                                    "timestamp": timestamp,
                                    "loop_number": loop_number,
                                    "blob_key": blob_key,
                                    "agreement_score": response_data.get("AGREEMENT_SCORE", ""),
                                    "convergence_momentum": response_data.get(
                                        "CONVERGENCE_MOMENTUM", ""
                                    ),
                                    "convergence_trend": response_data.get("CONVERGENCE_TREND", ""),
                                    "convergence_analysis": response_data.get(
                                        "CONVERGENCE_ANALYSIS", ""
                                    ),
                                    "emerging_consensus": response_data.get(
                                        "EMERGING_CONSENSUS", ""
                                    ),
                                    "continue_debate": response_data.get("CONTINUE_DEBATE", ""),
                                    "tokens": metrics.get("tokens", 0),
                                    "cost_usd": metrics.get("cost_usd", 0.0),
                                    "latency_ms": metrics.get("latency_ms", 0),
                                }
                                convergence_data.append(convergence_row)

                    except Exception:
                        continue

        return convergence_data

    def extract_token_cost_data(self):
        """Extract token usage and costs at agent level across loops"""
        token_cost_data = []

        for file_info in self.data:
            file_path = file_info["file_path"]
            data = file_info["data"]

            timestamp_match = re.search(r"(\d{8}_\d{6})", file_path)
            timestamp = timestamp_match.group(1) if timestamp_match else "unknown"

            blob_store = data.get("blob_store", {})
            for blob_key, blob_data in blob_store.items():
                if "result" in blob_data and "_metrics" in blob_data["result"]:
                    metrics = blob_data["result"]["_metrics"]

                    agent_type = self._extract_agent_type(blob_data)
                    loop_number = self._extract_loop_number(blob_data)

                    token_row = {
                        "file_path": file_path,
                        "timestamp": timestamp,
                        "loop_number": loop_number,
                        "agent_type": agent_type,
                        "blob_key": blob_key,
                        "total_tokens": metrics.get("tokens", 0),
                        "prompt_tokens": metrics.get("prompt_tokens", 0),
                        "completion_tokens": metrics.get("completion_tokens", 0),
                        "cost_usd": metrics.get("cost_usd", 0.0),
                        "latency_ms": metrics.get("latency_ms", 0),
                        "model": metrics.get("model", ""),
                        "status_code": metrics.get("status_code", 0),
                    }
                    token_cost_data.append(token_row)

        return token_cost_data

    def extract_influencer_data(self):
        """Extract most relevant/influencer agent per loop"""
        influencer_data = []

        # Group by loop and determine influencer based on tokens, cost, or specific roles
        loop_agents = defaultdict(list)

        for file_info in self.data:
            file_path = file_info["file_path"]
            data = file_info["data"]

            timestamp_match = re.search(r"(\d{8}_\d{6})", file_path)
            timestamp = timestamp_match.group(1) if timestamp_match else "unknown"

            blob_store = data.get("blob_store", {})
            for blob_key, blob_data in blob_store.items():
                if "result" in blob_data and "_metrics" in blob_data["result"]:
                    metrics = blob_data["result"]["_metrics"]
                    agent_type = self._extract_agent_type(blob_data)
                    loop_number = self._extract_loop_number(blob_data)

                    loop_key = f"{file_path}_{loop_number}"
                    loop_agents[loop_key].append(
                        {
                            "file_path": file_path,
                            "timestamp": timestamp,
                            "loop_number": loop_number,
                            "agent_type": agent_type,
                            "blob_key": blob_key,
                            "tokens": metrics.get("tokens", 0),
                            "cost_usd": metrics.get("cost_usd", 0.0),
                            "latency_ms": metrics.get("latency_ms", 0),
                        }
                    )

        # Find influencer (highest token usage) per loop
        for loop_key, agents in loop_agents.items():
            if agents:
                influencer = max(agents, key=lambda x: x["tokens"])
                influencer_data.append(influencer)

        return influencer_data

    def _extract_agent_type(self, blob_data) -> str:
        """Extract agent type from blob data"""
        # Check metadata first
        if "result" in blob_data and "metadata" in blob_data["result"]:
            metadata = blob_data["result"]["metadata"]
            if "agent_type" in metadata:
                return metadata["agent_type"]

        # Check input metadata
        if "input" in blob_data and "metadata" in blob_data["input"]:
            metadata = blob_data["input"]["metadata"]
            if "agent_type" in metadata:
                return metadata["agent_type"]

        # Check memory content
        if "result" in blob_data and "memories" in blob_data["result"]:
            memories = blob_data["result"]["memories"]
            if memories and isinstance(memories, list) and len(memories) > 0:
                memory = memories[0]
                if "metadata" in memory and "agent_type" in memory["metadata"]:
                    return memory["metadata"]["agent_type"]

        # Check formatted_prompt for agent type hints
        if "formatted_prompt" in blob_data:
            prompt = blob_data["formatted_prompt"]
            if "progressive" in prompt.lower():
                return "radical_progressive"
            elif "conservative" in prompt.lower():
                return "traditional_conservative"
            elif "realist" in prompt.lower():
                return "pragmatic_realist"
            elif "purist" in prompt.lower():
                return "ethical_purist"
            elif "advocate" in prompt.lower():
                return "devils_advocate"
            elif "moderator" in prompt.lower():
                return "neutral_moderator"

        return "unknown"

    def _extract_loop_number(self, blob_data) -> int:
        """Extract loop number from blob data"""
        # Check input data
        if "input" in blob_data and "loop_number" in blob_data["input"]:
            return blob_data["input"]["loop_number"]

        # Check result metadata
        if "result" in blob_data and "metadata" in blob_data["result"]:
            metadata = blob_data["result"]["metadata"]
            if "loop_number" in metadata:
                return int(metadata["loop_number"])

        # Check memory metadata
        if "result" in blob_data and "memories" in blob_data["result"]:
            memories = blob_data["result"]["memories"]
            if memories and isinstance(memories, list) and len(memories) > 0:
                memory = memories[0]
                if "metadata" in memory and "loop_number" in memory["metadata"]:
                    return int(memory["metadata"]["loop_number"])

        return 0

    def _extract_list_field(self, data: dict, field_name: str) -> str:
        """Extract list field and convert to string"""
        field_value = data.get(field_name, [])
        if isinstance(field_value, list):
            return " | ".join(str(item) for item in field_value)
        return str(field_value)

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

    def extract_all_data(self):
        """Extract all data types"""
        print("Loading data...")
        self.load_data()

        print("Extracting agent position data...")
        position_data = self.extract_agent_position_data()
        self.save_to_csv(position_data, "agent_positions.csv")

        print("Extracting attack/defense data...")
        defense_data = self.extract_attack_defense_data()
        self.save_to_csv(defense_data, "agent_attack_defense.csv")

        print("Extracting reasoning quality data...")
        quality_data = self.extract_reasoning_quality_data()
        self.save_to_csv(quality_data, "reasoning_quality.csv")

        print("Extracting convergence data...")
        convergence_data = self.extract_convergence_data()
        self.save_to_csv(convergence_data, "convergence_metrics.csv")

        print("Extracting token/cost data...")
        token_cost_data = self.extract_token_cost_data()
        self.save_to_csv(token_cost_data, "token_cost_data.csv")

        print("Extracting influencer data...")
        influencer_data = self.extract_influencer_data()
        self.save_to_csv(influencer_data, "influencer_agents.csv")

        print("Data extraction complete!")


def main():
    # Define file paths
    file_paths = [
        "logs/expSOC01/orka_trace_20250712_201756.json",
        "logs/expSOC01/orka_trace_20250712_201853.json",
        "logs/expSOC01/orka_trace_20250712_201954.json",
        "logs/expSOC01/orka_trace_20250712_202043.json",
    ]

    # Create extractor and run
    extractor = OrkaDataExtractor(file_paths)
    extractor.extract_all_data()


if __name__ == "__main__":
    main()
