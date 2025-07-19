#!/usr/bin/env python3
"""
Comprehensive Orka Data Extractor
Extracts all requested metrics from JSON log files and converts to CSV format.
Adapted for exp_local_SOC-02 directory files.
"""

import ast
import csv
import json
import re
from collections import defaultdict


class ComprehensiveOrkaExtractor:
    def __init__(self, file_paths: list[str]):
        self.file_paths = file_paths
        self.data = []
        self.all_data = []

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
                # Try to parse as JSON first
                try:
                    return json.loads(response_str)
                except json.JSONDecodeError:
                    try:
                        # If JSON fails, try literal_eval
                        return ast.literal_eval(response_str)
                    except (ValueError, SyntaxError):
                        # If literal_eval fails, try eval (less safe but sometimes necessary)
                        try:
                            return eval(response_str)
                        except Exception:
                            return {}
            return {}
        except Exception:
            return {}

    def extract_convergence_metrics(self):
        """Extract AGREEMENT_SCORE, CONVERGENCE_MOMENTUM, CONVERGENCE_TREND"""
        convergence_data = []

        for file_info in self.data:
            file_path = file_info["file_path"]
            data = file_info["data"]

            timestamp_match = re.search(r"(\d{8}_\d{6})", file_path)
            timestamp = timestamp_match.group(1) if timestamp_match else "unknown"

            print(f"Processing {file_path} for convergence data...")

            # Search through all data for convergence metrics
            blob_store = data.get("blob_store", {})

            for blob_key, blob_data in blob_store.items():
                found_convergence = False

                # Method 1: Check response field directly
                if "result" in blob_data and "response" in blob_data["result"]:
                    response_str = blob_data["result"]["response"]
                    response_data = self.safe_eval(response_str)

                    if any(
                        key in response_data
                        for key in [
                            "AGREEMENT_SCORE",
                            "CONVERGENCE_MOMENTUM",
                            "CONVERGENCE_TREND",
                            "CONVERGENCE_ANALYSIS",
                        ]
                    ):
                        print(f"Found convergence data in response: {blob_key[:20]}...")

                        loop_number = self._extract_loop_number(blob_data)
                        agent_type = self._extract_agent_type(blob_data)
                        metrics = blob_data.get("result", {}).get("_metrics", {})

                        convergence_row = {
                            "file_path": file_path,
                            "timestamp": timestamp,
                            "loop_number": loop_number,
                            "agent_type": agent_type,
                            "blob_key": blob_key,
                            "agreement_score": response_data.get("AGREEMENT_SCORE", ""),
                            "convergence_momentum": response_data.get("CONVERGENCE_MOMENTUM", ""),
                            "convergence_trend": response_data.get("CONVERGENCE_TREND", ""),
                            "convergence_analysis": response_data.get("CONVERGENCE_ANALYSIS", ""),
                            "emerging_consensus": response_data.get("EMERGING_CONSENSUS", ""),
                            "continue_debate": response_data.get("CONTINUE_DEBATE", ""),
                            "tokens": metrics.get("tokens", 0),
                            "cost_usd": metrics.get("cost_usd", 0.0),
                            "latency_ms": metrics.get("latency_ms", 0),
                        }
                        convergence_data.append(convergence_row)
                        found_convergence = True

                # Method 2: Check stored_metadata for agreement_score and convergence_trend
                if "result" in blob_data and "stored_metadata" in blob_data["result"]:
                    metadata = blob_data["result"]["stored_metadata"]

                    if "agreement_score" in metadata or "convergence_trend" in metadata:
                        print(f"Found convergence data in metadata: {blob_key[:20]}...")

                        # Parse agreement_score if it's a string containing the full dict
                        agreement_data = {}
                        if "agreement_score" in metadata:
                            agreement_score_str = metadata["agreement_score"]
                            if isinstance(agreement_score_str, str):
                                agreement_data = self.safe_eval(agreement_score_str)

                        loop_number = self._extract_loop_number(blob_data)
                        agent_type = metadata.get("agent_type", self._extract_agent_type(blob_data))

                        convergence_row = {
                            "file_path": file_path,
                            "timestamp": timestamp,
                            "loop_number": loop_number,
                            "agent_type": agent_type,
                            "blob_key": blob_key,
                            "agreement_score": agreement_data.get("AGREEMENT_SCORE", ""),
                            "convergence_momentum": agreement_data.get("CONVERGENCE_MOMENTUM", ""),
                            "convergence_trend": metadata.get(
                                "convergence_trend",
                                agreement_data.get("CONVERGENCE_TREND", ""),
                            ),
                            "convergence_analysis": agreement_data.get("CONVERGENCE_ANALYSIS", ""),
                            "emerging_consensus": agreement_data.get("EMERGING_CONSENSUS", ""),
                            "continue_debate": agreement_data.get("CONTINUE_DEBATE", ""),
                            "tokens": 0,
                            "cost_usd": 0.0,
                            "latency_ms": 0,
                        }
                        convergence_data.append(convergence_row)
                        found_convergence = True

                # Method 3: Check formatted_prompt for Agreement Assessment data
                if "formatted_prompt" in blob_data:
                    formatted_prompt = blob_data["formatted_prompt"]

                    # Look for Agreement Assessment patterns
                    if (
                        "Agreement Assessment:" in formatted_prompt
                        or "AGREEMENT_SCORE" in formatted_prompt
                    ):
                        # Extract the agreement data from the formatted prompt
                        patterns = [
                            r"Agreement Assessment: ({[^}]+})",
                            r"'AGREEMENT_SCORE': ([0-9.]+)",
                            r"\"AGREEMENT_SCORE\": ([0-9.]+)",
                        ]

                        for pattern in patterns:
                            matches = re.findall(pattern, formatted_prompt)
                            if matches:
                                print(
                                    f"Found convergence data in formatted_prompt: {blob_key[:20]}...",
                                )

                                loop_number = self._extract_loop_number(blob_data)
                                agent_type = self._extract_agent_type(blob_data)

                                # Try to parse the first match as agreement data
                                if matches[0].startswith("{"):
                                    agreement_data = self.safe_eval(matches[0])
                                else:
                                    agreement_data = {
                                        "AGREEMENT_SCORE": (
                                            float(matches[0])
                                            if matches[0].replace(".", "").isdigit()
                                            else matches[0]
                                        ),
                                    }

                                convergence_row = {
                                    "file_path": file_path,
                                    "timestamp": timestamp,
                                    "loop_number": loop_number,
                                    "agent_type": agent_type,
                                    "blob_key": blob_key,
                                    "agreement_score": agreement_data.get("AGREEMENT_SCORE", ""),
                                    "convergence_momentum": agreement_data.get(
                                        "CONVERGENCE_MOMENTUM",
                                        "",
                                    ),
                                    "convergence_trend": agreement_data.get(
                                        "CONVERGENCE_TREND",
                                        "",
                                    ),
                                    "convergence_analysis": agreement_data.get(
                                        "CONVERGENCE_ANALYSIS",
                                        "",
                                    ),
                                    "emerging_consensus": agreement_data.get(
                                        "EMERGING_CONSENSUS",
                                        "",
                                    ),
                                    "continue_debate": agreement_data.get("CONTINUE_DEBATE", ""),
                                    "tokens": 0,
                                    "cost_usd": 0.0,
                                    "latency_ms": 0,
                                }
                                convergence_data.append(convergence_row)
                                found_convergence = True
                                break

                # Method 4: Check past_loops in input for historical agreement scores
                input_data = blob_data.get("input", {})
                if isinstance(input_data, dict) and "past_loops" in input_data:
                    past_loops = input_data["past_loops"]
                    for loop_info in past_loops:
                        if "agreement_score" in loop_info:
                            print(
                                f"Found past loop agreement score: {loop_info.get('agreement_score')}",
                            )
                            convergence_row = {
                                "file_path": file_path,
                                "timestamp": timestamp,
                                "loop_number": loop_info.get("round", 0),
                                "agent_type": "system",
                                "blob_key": blob_key,
                                "agreement_score": loop_info.get("agreement_score", ""),
                                "convergence_momentum": "",
                                "convergence_trend": "",
                                "convergence_analysis": "",
                                "emerging_consensus": "",
                                "continue_debate": "",
                                "tokens": 0,
                                "cost_usd": 0.0,
                                "latency_ms": 0,
                            }
                            convergence_data.append(convergence_row)
                            found_convergence = True

        print(f"Total convergence records found: {len(convergence_data)}")
        return convergence_data

    def extract_quality_metrics(self):
        """Extract REASONING_QUALITY, QUALITY_ANALYSIS, PRODUCTIVE_DISAGREEMENTS"""
        quality_data = []

        for file_info in self.data:
            file_path = file_info["file_path"]
            data = file_info["data"]

            timestamp_match = re.search(r"(\d{8}_\d{6})", file_path)
            timestamp = timestamp_match.group(1) if timestamp_match else "unknown"

            blob_store = data.get("blob_store", {})
            for blob_key, blob_data in blob_store.items():
                response_str = ""
                if "result" in blob_data and "response" in blob_data["result"]:
                    response_str = blob_data["result"]["response"]

                if response_str:
                    response_data = self.safe_eval(response_str)

                    if any(
                        key in response_data
                        for key in [
                            "REASONING_QUALITY",
                            "QUALITY_ANALYSIS",
                            "PRODUCTIVE_DISAGREEMENTS",
                        ]
                    ):
                        loop_number = self._extract_loop_number(blob_data)
                        agent_type = self._extract_agent_type(blob_data)
                        metrics = blob_data.get("result", {}).get("_metrics", {})

                        quality_row = {
                            "file_path": file_path,
                            "timestamp": timestamp,
                            "loop_number": loop_number,
                            "agent_type": agent_type,
                            "blob_key": blob_key,
                            "reasoning_quality": response_data.get("REASONING_QUALITY", ""),
                            "quality_analysis": response_data.get("QUALITY_ANALYSIS", ""),
                            "productive_disagreements": response_data.get(
                                "PRODUCTIVE_DISAGREEMENTS",
                                "",
                            ),
                            "tokens": metrics.get("tokens", 0),
                            "cost_usd": metrics.get("cost_usd", 0.0),
                            "latency_ms": metrics.get("latency_ms", 0),
                        }
                        quality_data.append(quality_row)

        return quality_data

    def extract_workflow_costs(self):
        """Extract costs at workflow level"""
        workflow_costs = []

        for file_info in self.data:
            file_path = file_info["file_path"]
            data = file_info["data"]

            timestamp_match = re.search(r"(\d{8}_\d{6})", file_path)
            timestamp = timestamp_match.group(1) if timestamp_match else "unknown"

            # Look for workflow-level cost data
            metadata = data.get("_metadata", {})

            # Check for total costs in metadata
            total_cost = 0.0
            total_tokens = 0

            blob_store = data.get("blob_store", {})
            for blob_key, blob_data in blob_store.items():
                metrics = blob_data.get("result", {}).get("_metrics", {})
                if metrics:
                    total_cost += metrics.get("cost_usd", 0.0)
                    total_tokens += metrics.get("tokens", 0)

            workflow_row = {
                "file_path": file_path,
                "timestamp": timestamp,
                "workflow_total_cost": total_cost,
                "workflow_total_tokens": total_tokens,
                "blob_count": len(blob_store),
                "metadata_entries": metadata.get("total_entries", 0),
                "size_reduction": metadata.get("stats", {}).get("size_reduction", 0),
            }
            workflow_costs.append(workflow_row)

        return workflow_costs

    def extract_loop_summaries(self):
        """Extract loop-level summaries"""
        loop_summaries = []

        for file_info in self.data:
            file_path = file_info["file_path"]
            data = file_info["data"]

            timestamp_match = re.search(r"(\d{8}_\d{6})", file_path)
            timestamp = timestamp_match.group(1) if timestamp_match else "unknown"

            # Group by loop number
            loop_data = defaultdict(
                lambda: {
                    "agents": [],
                    "total_tokens": 0,
                    "total_cost": 0.0,
                    "avg_latency": 0.0,
                    "models": set(),
                },
            )

            blob_store = data.get("blob_store", {})
            for blob_key, blob_data in blob_store.items():
                loop_number = self._extract_loop_number(blob_data)
                agent_type = self._extract_agent_type(blob_data)
                metrics = blob_data.get("result", {}).get("_metrics", {})

                if metrics:
                    loop_data[loop_number]["agents"].append(agent_type)
                    loop_data[loop_number]["total_tokens"] += metrics.get("tokens", 0)
                    loop_data[loop_number]["total_cost"] += metrics.get("cost_usd", 0.0)
                    loop_data[loop_number]["avg_latency"] += metrics.get("latency_ms", 0)
                    if metrics.get("model"):
                        loop_data[loop_number]["models"].add(metrics["model"])

            # Create summary rows
            for loop_number, loop_info in loop_data.items():
                if loop_info["agents"]:
                    avg_latency = loop_info["avg_latency"] / len(loop_info["agents"])

                    summary_row = {
                        "file_path": file_path,
                        "timestamp": timestamp,
                        "loop_number": loop_number,
                        "agent_count": len(loop_info["agents"]),
                        "unique_agents": len(set(loop_info["agents"])),
                        "total_tokens": loop_info["total_tokens"],
                        "total_cost": loop_info["total_cost"],
                        "avg_latency": avg_latency,
                        "models_used": " | ".join(loop_info["models"]),
                        "agents_involved": " | ".join(set(loop_info["agents"])),
                    }
                    loop_summaries.append(summary_row)

        return loop_summaries

    def extract_agent_performance(self):
        """Extract agent performance metrics across all loops"""
        agent_performance = []

        # Group by agent type across all files
        agent_data = defaultdict(
            lambda: {
                "total_tokens": 0,
                "total_cost": 0.0,
                "total_latency": 0.0,
                "appearances": 0,
                "loops": set(),
                "files": set(),
            },
        )

        for file_info in self.data:
            file_path = file_info["file_path"]
            data = file_info["data"]

            timestamp_match = re.search(r"(\d{8}_\d{6})", file_path)
            timestamp = timestamp_match.group(1) if timestamp_match else "unknown"

            blob_store = data.get("blob_store", {})
            for blob_key, blob_data in blob_store.items():
                agent_type = self._extract_agent_type(blob_data)
                loop_number = self._extract_loop_number(blob_data)
                metrics = blob_data.get("result", {}).get("_metrics", {})

                if metrics and agent_type != "unknown":
                    agent_data[agent_type]["total_tokens"] += metrics.get("tokens", 0)
                    agent_data[agent_type]["total_cost"] += metrics.get("cost_usd", 0.0)
                    agent_data[agent_type]["total_latency"] += metrics.get("latency_ms", 0)
                    agent_data[agent_type]["appearances"] += 1
                    agent_data[agent_type]["loops"].add(loop_number)
                    agent_data[agent_type]["files"].add(file_path)

        # Create performance summary
        for agent_type, data in agent_data.items():
            if data["appearances"] > 0:
                performance_row = {
                    "agent_type": agent_type,
                    "total_tokens": data["total_tokens"],
                    "total_cost": data["total_cost"],
                    "avg_tokens_per_appearance": data["total_tokens"] / data["appearances"],
                    "avg_cost_per_appearance": data["total_cost"] / data["appearances"],
                    "avg_latency": data["total_latency"] / data["appearances"],
                    "total_appearances": data["appearances"],
                    "loops_participated": len(data["loops"]),
                    "files_appeared": len(data["files"]),
                    "loops_list": " | ".join(str(l) for l in sorted(data["loops"])),
                }
                agent_performance.append(performance_row)

        return agent_performance

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

    def extract_all_comprehensive_data(self):
        """Extract all comprehensive data"""
        print("Loading data...")
        self.load_data()

        print("Extracting convergence metrics...")
        convergence_data = self.extract_convergence_metrics()
        self.save_to_csv(convergence_data, "convergence_metrics_detailed.csv")

        print("Extracting quality metrics...")
        quality_data = self.extract_quality_metrics()
        self.save_to_csv(quality_data, "quality_metrics_detailed.csv")

        print("Extracting workflow costs...")
        workflow_costs = self.extract_workflow_costs()
        self.save_to_csv(workflow_costs, "workflow_costs.csv")

        print("Extracting loop summaries...")
        loop_summaries = self.extract_loop_summaries()
        self.save_to_csv(loop_summaries, "loop_summaries.csv")

        print("Extracting agent performance...")
        agent_performance = self.extract_agent_performance()
        self.save_to_csv(agent_performance, "agent_performance.csv")

        print("Comprehensive data extraction complete!")


def main():
    # Define file paths for current directory
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

    # Create extractor and run
    extractor = ComprehensiveOrkaExtractor(file_paths)
    extractor.extract_all_comprehensive_data()


if __name__ == "__main__":
    main()
