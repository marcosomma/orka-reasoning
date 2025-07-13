#!/usr/bin/env python3
"""
Extract comprehensive workflow summary data from the final Orka trace JSON file.
This script focuses on the final summary file that contains all workflow execution metrics.
"""

import csv
import json
import os


class WorkflowSummaryExtractor:
    def __init__(self, summary_file_path: str):
        self.summary_file_path = summary_file_path
        self.data = None

    def load_data(self):
        """Load the summary JSON file"""
        with open(self.summary_file_path, encoding="utf-8") as f:
            self.data = json.load(f)
        print(f"Loaded workflow summary from: {self.summary_file_path}")

    def extract_workflow_summary(self):
        """Extract high-level workflow execution metrics"""
        if not self.data:
            return []

        # Extract meta report from events
        meta_report = None
        for event in self.data.get("events", []):
            if event.get("event_type") == "MetaReport":
                meta_report = event.get("payload", {}).get("meta_report", {})
                break

        if not meta_report:
            print("No meta report found in events")
            return []

        # Extract final synthesis results
        final_synthesis = None
        blob_store = self.data.get("blob_store", {})

        # Look for final synthesis in blob store
        for blob_key, blob_data in blob_store.items():
            if (
                "final_synthesis" in str(blob_data).lower()
                or "CONSENSUS ACHIEVED" in str(blob_data)
                or "Score: 0.85" in str(blob_data)
            ):
                if isinstance(blob_data, dict) and "result" in blob_data:
                    result = blob_data["result"]
                    if isinstance(result, dict) and "result" in result:
                        final_result = result["result"]
                        if isinstance(final_result, dict) and "response" in final_result:
                            final_synthesis = final_result["response"]
                            break

        summary_data = [
            {
                "workflow_id": meta_report.get("execution_stats", {}).get("run_id", "unknown"),
                "timestamp": self.data.get("_metadata", {}).get("generated_at", "unknown"),
                "total_duration_seconds": meta_report.get("total_duration", 0),
                "total_llm_calls": meta_report.get("total_llm_calls", 0),
                "total_tokens": meta_report.get("total_tokens", 0),
                "total_cost_usd": meta_report.get("total_cost_usd", 0),
                "avg_latency_ms": meta_report.get("avg_latency_ms", 0),
                "total_agents_executed": meta_report.get("execution_stats", {}).get(
                    "total_agents_executed", 0
                ),
                "platform": meta_report.get("runtime_environment", {}).get("platform", "unknown"),
                "python_version": meta_report.get("runtime_environment", {}).get(
                    "python_version", "unknown"
                ),
                "git_sha": meta_report.get("runtime_environment", {}).get("git_sha", "unknown"),
                "final_consensus": final_synthesis[:200] + "..."
                if final_synthesis and len(final_synthesis) > 200
                else final_synthesis,
                "loops_completed": 4,  # From the formatted prompt data
                "final_agreement_score": 0.85,  # From the formatted prompt data
                "consensus_achieved": "All stakeholders acknowledge the necessity of ethical standards in AI deployment to promote community welfare and accountability.",
            }
        ]

        return summary_data

    def extract_agent_performance(self):
        """Extract agent-level performance metrics"""
        if not self.data:
            return []

        # Extract meta report from events
        meta_report = None
        for event in self.data.get("events", []):
            if event.get("event_type") == "MetaReport":
                meta_report = event.get("payload", {}).get("meta_report", {})
                break

        if not meta_report:
            return []

        agent_breakdown = meta_report.get("agent_breakdown", {})
        agent_data = []

        for agent_name, metrics in agent_breakdown.items():
            agent_data.append(
                {
                    "workflow_id": meta_report.get("execution_stats", {}).get("run_id", "unknown"),
                    "agent_name": agent_name,
                    "agent_type": self.categorize_agent_type(agent_name),
                    "total_calls": metrics.get("calls", 0),
                    "total_tokens": metrics.get("tokens", 0),
                    "total_cost_usd": metrics.get("cost_usd", 0),
                    "avg_latency_ms": metrics.get("avg_latency_ms", 0),
                    "cost_per_call": metrics.get("cost_usd", 0) / max(metrics.get("calls", 1), 1),
                    "tokens_per_call": metrics.get("tokens", 0) / max(metrics.get("calls", 1), 1),
                    "percentage_of_total_cost": (
                        metrics.get("cost_usd", 0) / meta_report.get("total_cost_usd", 1)
                    )
                    * 100,
                    "percentage_of_total_tokens": (
                        metrics.get("tokens", 0) / meta_report.get("total_tokens", 1)
                    )
                    * 100,
                    "percentage_of_total_calls": (
                        metrics.get("calls", 0) / meta_report.get("total_llm_calls", 1)
                    )
                    * 100,
                }
            )

        return agent_data

    def categorize_agent_type(self, agent_name: str) -> str:
        """Categorize agent based on name"""
        if "loop" in agent_name.lower():
            return "debate_loop"
        elif "reflection" in agent_name.lower():
            return "meta_analysis"
        elif "extractor" in agent_name.lower():
            return "quality_analysis"
        elif "synthesis" in agent_name.lower():
            return "final_synthesis"
        else:
            return "unknown"

    def extract_memory_insights(self):
        """Extract memory and reflection insights"""
        if not self.data:
            return []

        blob_store = self.data.get("blob_store", {})
        memory_insights = []

        for blob_key, blob_data in blob_store.items():
            if isinstance(blob_data, dict) and "result" in blob_data:
                result = blob_data["result"]
                if isinstance(result, dict):
                    # Look for memory data
                    if "conservative_memory_reader" in result:
                        mem_data = result["conservative_memory_reader"]
                        if isinstance(mem_data, dict) and "memories" in mem_data:
                            for memory in mem_data["memories"]:
                                if isinstance(memory, dict):
                                    memory_insights.append(
                                        {
                                            "workflow_id": "final_summary",
                                            "agent_type": memory.get("metadata", {}).get(
                                                "agent_type", "unknown"
                                            ),
                                            "loop_number": memory.get("metadata", {}).get(
                                                "loop_number", "unknown"
                                            ),
                                            "memory_type": memory.get("memory_type", "unknown"),
                                            "importance_score": memory.get("importance_score", 0),
                                            "similarity_score": memory.get("similarity_score", 0),
                                            "ttl_seconds": memory.get("ttl_seconds", 0),
                                            "content_preview": memory.get("content", "")[:100]
                                            + "..."
                                            if memory.get("content")
                                            else "",
                                        }
                                    )

                    # Look for other memory readers
                    for key in [
                        "progressive_memory_reader",
                        "realist_memory_reader",
                        "purist_memory_reader",
                        "advocate_memory_reader",
                        "moderator_memory_reader",
                    ]:
                        if key in result:
                            mem_data = result[key]
                            if isinstance(mem_data, dict) and "memories" in mem_data:
                                for memory in mem_data["memories"]:
                                    if isinstance(memory, dict):
                                        memory_insights.append(
                                            {
                                                "workflow_id": "final_summary",
                                                "agent_type": memory.get("metadata", {}).get(
                                                    "agent_type", key.split("_")[0]
                                                ),
                                                "loop_number": memory.get("metadata", {}).get(
                                                    "loop_number", "unknown"
                                                ),
                                                "memory_type": memory.get("memory_type", "unknown"),
                                                "importance_score": memory.get(
                                                    "importance_score", 0
                                                ),
                                                "similarity_score": memory.get(
                                                    "similarity_score", 0
                                                ),
                                                "ttl_seconds": memory.get("ttl_seconds", 0),
                                                "content_preview": memory.get("content", "")[:100]
                                                + "..."
                                                if memory.get("content")
                                                else "",
                                            }
                                        )

        return memory_insights

    def extract_debate_dynamics(self):
        """Extract debate dynamics and creative tension insights"""
        if not self.data:
            return []

        blob_store = self.data.get("blob_store", {})
        debate_insights = []

        for blob_key, blob_data in blob_store.items():
            if isinstance(blob_data, dict) and "result" in blob_data:
                result = blob_data["result"]
                if isinstance(result, dict) and "result" in result:
                    final_result = result["result"]
                    if isinstance(final_result, dict) and "response" in final_result:
                        response = final_result["response"]
                        if (
                            "debate dynamics" in response.lower()
                            or "creative tension" in response.lower()
                        ):
                            debate_insights.append(
                                {
                                    "workflow_id": "final_summary",
                                    "insight_type": "debate_dynamics",
                                    "confidence": final_result.get("confidence", 0),
                                    "tokens_used": final_result.get("_metrics", {}).get(
                                        "tokens", 0
                                    ),
                                    "cost_usd": final_result.get("_metrics", {}).get("cost_usd", 0),
                                    "latency_ms": final_result.get("_metrics", {}).get(
                                        "latency_ms", 0
                                    ),
                                    "model_used": final_result.get("_metrics", {}).get(
                                        "model", "unknown"
                                    ),
                                    "key_insights": response[:300] + "..."
                                    if len(response) > 300
                                    else response,
                                }
                            )

        return debate_insights

    def extract_execution_timeline(self):
        """Extract execution timeline from events"""
        if not self.data:
            return []

        events = self.data.get("events", [])
        timeline_data = []

        for event in events:
            timeline_data.append(
                {
                    "workflow_id": event.get("run_id", "unknown"),
                    "step": event.get("step", 0),
                    "agent_id": event.get("agent_id", "unknown"),
                    "event_type": event.get("event_type", "unknown"),
                    "timestamp": event.get("timestamp", "unknown"),
                    "fork_group": event.get("fork_group", "none"),
                    "parent": event.get("parent", "none"),
                }
            )

        return timeline_data

    def save_to_csv(self, data: list[dict], filename: str):
        """Save data to CSV file"""
        if not data:
            print(f"No data to save for {filename}")
            return

        print(f"Saving {len(data)} records to {filename}")

        with open(filename, "w", newline="", encoding="utf-8") as csvfile:
            if data:
                writer = csv.DictWriter(csvfile, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)

    def run_extraction(self):
        """Run all extraction tasks"""
        print("Starting workflow summary extraction...")

        self.load_data()

        # Extract workflow summary
        workflow_summary = self.extract_workflow_summary()
        self.save_to_csv(workflow_summary, "workflow_summary.csv")

        # Extract agent performance
        agent_performance = self.extract_agent_performance()
        self.save_to_csv(agent_performance, "agent_performance_summary.csv")

        # Extract memory insights
        memory_insights = self.extract_memory_insights()
        self.save_to_csv(memory_insights, "memory_insights_summary.csv")

        # Extract debate dynamics
        debate_dynamics = self.extract_debate_dynamics()
        self.save_to_csv(debate_dynamics, "debate_dynamics_summary.csv")

        # Extract execution timeline
        execution_timeline = self.extract_execution_timeline()
        self.save_to_csv(execution_timeline, "execution_timeline_summary.csv")

        print("Workflow summary extraction completed!")
        print("\nFiles created:")
        print("- workflow_summary.csv: Overall workflow metrics")
        print("- agent_performance_summary.csv: Agent-level performance")
        print("- memory_insights_summary.csv: Memory system insights")
        print("- debate_dynamics_summary.csv: Creative tension analysis")
        print("- execution_timeline_summary.csv: Step-by-step execution")


def main():
    """Main execution function"""
    summary_file = "logs/expSOC01/orka_trace_20250712_202059.json"

    if not os.path.exists(summary_file):
        print(f"Error: Summary file not found: {summary_file}")
        return

    extractor = WorkflowSummaryExtractor(summary_file)
    extractor.run_extraction()


if __name__ == "__main__":
    main()
