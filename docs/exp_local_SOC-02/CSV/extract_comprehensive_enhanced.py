#!/usr/bin/env python3
"""
Enhanced Comprehensive Orka Data Extractor
Extracts detailed analysis data including debate dynamics, quality metrics, convergence analysis,
and agent interaction patterns from JSON log files.
"""

import csv
import json
import re
from collections import defaultdict


class EnhancedOrkaExtractor:
    def __init__(self, file_paths: list[str]):
        self.file_paths = file_paths
        self.data = []
        self.all_responses = []
        self.agent_interactions = []
        self.quality_metrics = []
        self.convergence_data = []
        self.debate_dynamics = []
        self.execution_timeline = []
        self.memory_usage = []

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
                            "timestamp": self._extract_timestamp(file_path),
                        }
                    )
                    print(f"Loaded {file_path}")
            except Exception as e:
                print(f"Error loading {file_path}: {e}")

    def _extract_timestamp(self, file_path: str) -> str:
        """Extract timestamp from file path"""
        match = re.search(r"(\d{8}_\d{6})", file_path)
        return match.group(1) if match else "unknown"

    def extract_detailed_responses(self):
        """Extract detailed response analysis"""
        detailed_responses = []

        for file_info in self.data:
            file_path = file_info["file_path"]
            data = file_info["data"]
            timestamp = file_info["timestamp"]

            blob_store = data.get("blob_store", {})

            for blob_key, blob_data in blob_store.items():
                if "result" in blob_data and "response" in blob_data["result"]:
                    response_text = blob_data["result"]["response"]

                    # Extract structured content
                    position = self._extract_position(response_text)
                    arguments = self._extract_arguments(response_text)
                    collaboration = self._extract_collaboration(response_text)

                    # Agent type analysis
                    agent_type = self._extract_agent_type_from_prompt(
                        blob_data.get("formatted_prompt", ""),
                    )

                    # Quality metrics
                    quality_score = self._calculate_quality_score(response_text)
                    reasoning_depth = self._calculate_reasoning_depth(response_text)
                    coherence_score = self._calculate_coherence_score(response_text)

                    detailed_responses.append(
                        {
                            "file_path": file_path,
                            "timestamp": timestamp,
                            "blob_key": blob_key,
                            "agent_type": agent_type,
                            "position": position,
                            "arguments": arguments,
                            "collaboration": collaboration,
                            "response_length": len(response_text),
                            "quality_score": quality_score,
                            "reasoning_depth": reasoning_depth,
                            "coherence_score": coherence_score,
                            "full_response": response_text[:500] + "..."
                            if len(response_text) > 500
                            else response_text,
                        }
                    )

        return detailed_responses

    def extract_debate_dynamics(self):
        """Extract debate dynamics and argument flow"""
        debate_dynamics = []

        # Group responses by timestamp to analyze interactions
        timestamp_groups = defaultdict(list)

        for file_info in self.data:
            file_path = file_info["file_path"]
            data = file_info["data"]
            timestamp = file_info["timestamp"]

            blob_store = data.get("blob_store", {})

            for blob_key, blob_data in blob_store.items():
                if "result" in blob_data and "response" in blob_data["result"]:
                    response_text = blob_data["result"]["response"]
                    agent_type = self._extract_agent_type_from_prompt(
                        blob_data.get("formatted_prompt", ""),
                    )

                    timestamp_groups[timestamp].append(
                        {
                            "agent_type": agent_type,
                            "response": response_text,
                            "blob_key": blob_key,
                            "file_path": file_path,
                        }
                    )

        # Analyze interactions within each timestamp group
        for timestamp, responses in timestamp_groups.items():
            if len(responses) > 1:  # Only analyze if multiple agents responded
                for i, response in enumerate(responses):
                    # Find references to other perspectives
                    references = self._find_perspective_references(response["response"])

                    debate_dynamics.append(
                        {
                            "timestamp": timestamp,
                            "agent_type": response["agent_type"],
                            "response_order": i + 1,
                            "total_agents": len(responses),
                            "references_to_others": len(references),
                            "referenced_perspectives": " | ".join(references),
                            "argument_strength": self._calculate_argument_strength(
                                response["response"]
                            ),
                            "confrontational_tone": self._detect_confrontational_tone(
                                response["response"]
                            ),
                            "collaborative_tone": self._detect_collaborative_tone(
                                response["response"]
                            ),
                            "file_path": response["file_path"],
                        }
                    )

        return debate_dynamics

    def extract_convergence_analysis(self):
        """Extract convergence and consensus analysis"""
        convergence_analysis = []

        # Track position changes over time
        agent_positions = defaultdict(list)

        for file_info in self.data:
            file_path = file_info["file_path"]
            data = file_info["data"]
            timestamp = file_info["timestamp"]

            blob_store = data.get("blob_store", {})

            for blob_key, blob_data in blob_store.items():
                if "result" in blob_data and "response" in blob_data["result"]:
                    response_text = blob_data["result"]["response"]
                    agent_type = self._extract_agent_type_from_prompt(
                        blob_data.get("formatted_prompt", ""),
                    )

                    position = self._extract_position(response_text)

                    agent_positions[agent_type].append(
                        {
                            "timestamp": timestamp,
                            "position": position,
                            "file_path": file_path,
                        }
                    )

        # Analyze convergence patterns
        for agent_type, positions in agent_positions.items():
            if len(positions) > 1:  # Only analyze if multiple positions exist
                for i, position in enumerate(positions):
                    convergence_analysis.append(
                        {
                            "agent_type": agent_type,
                            "timestamp": position["timestamp"],
                            "position_number": i + 1,
                            "total_positions": len(positions),
                            "position_length": len(position["position"]),
                            "position_consistency": self._calculate_position_consistency(
                                positions, i
                            ),
                            "convergence_indicator": self._detect_convergence_indicators(
                                position["position"]
                            ),
                            "file_path": position["file_path"],
                        }
                    )

        return convergence_analysis

    def extract_quality_metrics(self):
        """Extract detailed quality metrics"""
        quality_metrics = []

        for file_info in self.data:
            file_path = file_info["file_path"]
            data = file_info["data"]
            timestamp = file_info["timestamp"]

            blob_store = data.get("blob_store", {})

            for blob_key, blob_data in blob_store.items():
                if "result" in blob_data and "response" in blob_data["result"]:
                    response_text = blob_data["result"]["response"]
                    agent_type = self._extract_agent_type_from_prompt(
                        blob_data.get("formatted_prompt", ""),
                    )

                    quality_metrics.append(
                        {
                            "file_path": file_path,
                            "timestamp": timestamp,
                            "agent_type": agent_type,
                            "blob_key": blob_key,
                            "response_length": len(response_text),
                            "argument_count": self._count_arguments(response_text),
                            "evidence_count": self._count_evidence(response_text),
                            "logical_connectors": self._count_logical_connectors(response_text),
                            "complexity_score": self._calculate_complexity_score(response_text),
                            "clarity_score": self._calculate_clarity_score(response_text),
                            "novelty_score": self._calculate_novelty_score(response_text),
                            "coherence_score": self._calculate_coherence_score(response_text),
                            "overall_quality": self._calculate_overall_quality(response_text),
                        }
                    )

        return quality_metrics

    def extract_execution_timeline(self):
        """Extract detailed execution timeline"""
        execution_timeline = []

        for file_info in self.data:
            file_path = file_info["file_path"]
            data = file_info["data"]
            timestamp = file_info["timestamp"]
            metadata = file_info["metadata"]

            blob_store = data.get("blob_store", {})

            # Extract overall workflow timing
            total_blobs = metadata.get("total_blobs_stored", 0)
            size_reduction = metadata.get("stats", {}).get("size_reduction", 0)

            execution_timeline.append(
                {
                    "file_path": file_path,
                    "timestamp": timestamp,
                    "total_blobs": total_blobs,
                    "size_reduction": size_reduction,
                    "blob_efficiency": size_reduction / max(1, total_blobs),
                    "agents_active": len(
                        set(
                            self._extract_agent_type_from_prompt(
                                blob_data.get("formatted_prompt", "")
                            )
                            for blob_data in blob_store.values()
                        )
                    ),
                    "response_diversity": self._calculate_response_diversity(blob_store),
                    "processing_complexity": self._calculate_processing_complexity(blob_store),
                }
            )

        return execution_timeline

    def extract_memory_usage(self):
        """Extract memory usage analysis"""
        memory_usage = []

        for file_info in self.data:
            file_path = file_info["file_path"]
            data = file_info["data"]
            timestamp = file_info["timestamp"]

            blob_store = data.get("blob_store", {})

            for blob_key, blob_data in blob_store.items():
                memories = blob_data.get("result", {}).get("memories", [])

                memory_usage.append(
                    {
                        "file_path": file_path,
                        "timestamp": timestamp,
                        "blob_key": blob_key,
                        "memory_count": len(memories),
                        "memory_relevance": self._calculate_memory_relevance(memories),
                        "memory_diversity": self._calculate_memory_diversity(memories),
                        "memory_recency": self._calculate_memory_recency(memories),
                        "memory_utilization": self._calculate_memory_utilization(
                            memories, blob_data
                        ),
                    }
                )

        return memory_usage

    # Helper methods for analysis
    def _extract_position(self, response_text: str) -> str:
        """Extract POSITION section from response"""
        match = re.search(r"POSITION:\s*(.+?)(?=\n\n|\nARGUMENTS:|$)", response_text, re.DOTALL)
        return match.group(1).strip() if match else ""

    def _extract_arguments(self, response_text: str) -> str:
        """Extract ARGUMENTS section from response"""
        match = re.search(
            r"ARGUMENTS:\s*(.+?)(?=\n\n|\nCOLLABORATION:|$)", response_text, re.DOTALL
        )
        return match.group(1).strip() if match else ""

    def _extract_collaboration(self, response_text: str) -> str:
        """Extract COLLABORATION section from response"""
        match = re.search(r"COLLABORATION:\s*(.+?)(?=\n\n|$)", response_text, re.DOTALL)
        return match.group(1).strip() if match else ""

    def _extract_agent_type_from_prompt(self, prompt: str) -> str:
        """Extract agent type from formatted prompt"""
        prompt_lower = prompt.lower()
        if "progressive" in prompt_lower:
            return "progressive"
        elif "conservative" in prompt_lower:
            return "conservative"
        elif "realist" in prompt_lower:
            return "realist"
        elif "purist" in prompt_lower:
            return "purist"
        elif "advocate" in prompt_lower:
            return "devils_advocate"
        return "unknown"

    def _calculate_quality_score(self, response_text: str) -> float:
        """Calculate overall quality score"""
        # Simple quality scoring based on structure and content
        score = 0
        if "POSITION:" in response_text:
            score += 2
        if "ARGUMENTS:" in response_text:
            score += 2
        if "COLLABORATION:" in response_text:
            score += 2

        # Additional scoring for depth and reasoning
        reasoning_words = ["because", "therefore", "thus", "however", "furthermore"]
        for word in reasoning_words:
            if word in response_text.lower():
                score += 0.5

        return min(10, score)

    def _calculate_reasoning_depth(self, response_text: str) -> int:
        """Calculate reasoning depth based on logical structure"""
        depth_indicators = [
            "1)",
            "2)",
            "3)",
            "firstly",
            "secondly",
            "thirdly",
            "moreover",
            "furthermore",
        ]
        return sum(1 for indicator in depth_indicators if indicator in response_text.lower())

    def _calculate_coherence_score(self, response_text: str) -> float:
        """Calculate coherence score based on logical flow"""
        connectors = ["therefore", "however", "moreover", "furthermore", "consequently", "thus"]
        connector_count = sum(1 for connector in connectors if connector in response_text.lower())
        words = len(response_text.split())
        return min(10, (connector_count / max(1, words // 100)) * 10)

    def _find_perspective_references(self, response_text: str) -> list:
        """Find references to other perspectives"""
        perspectives = ["progressive", "conservative", "realist", "purist", "advocate"]
        found = []
        for perspective in perspectives:
            if perspective in response_text.lower():
                found.append(perspective)
        return found

    def _calculate_argument_strength(self, response_text: str) -> float:
        """Calculate argument strength based on evidence and reasoning"""
        evidence_words = ["evidence", "proof", "data", "research", "studies", "analysis"]
        evidence_count = sum(1 for word in evidence_words if word in response_text.lower())
        return min(10, evidence_count * 1.5)

    def _detect_confrontational_tone(self, response_text: str) -> bool:
        """Detect confrontational tone"""
        confrontational_words = ["wrong", "incorrect", "disagree", "oppose", "reject", "fallacy"]
        return any(word in response_text.lower() for word in confrontational_words)

    def _detect_collaborative_tone(self, response_text: str) -> bool:
        """Detect collaborative tone"""
        collaborative_words = ["collaborate", "together", "agree", "support", "build", "enhance"]
        return any(word in response_text.lower() for word in collaborative_words)

    def _calculate_position_consistency(self, positions: list, current_index: int) -> float:
        """Calculate position consistency over time"""
        if current_index == 0:
            return 1.0

        current_pos = positions[current_index]["position"]
        previous_pos = positions[current_index - 1]["position"]

        # Simple similarity measure
        common_words = set(current_pos.lower().split()) & set(previous_pos.lower().split())
        total_words = len(set(current_pos.lower().split()) | set(previous_pos.lower().split()))

        return len(common_words) / max(1, total_words)

    def _detect_convergence_indicators(self, position: str) -> bool:
        """Detect convergence indicators in position"""
        convergence_words = ["consensus", "agreement", "common", "shared", "unified", "together"]
        return any(word in position.lower() for word in convergence_words)

    def _count_arguments(self, response_text: str) -> int:
        """Count numbered arguments"""
        return len(re.findall(r"\d+\)", response_text))

    def _count_evidence(self, response_text: str) -> int:
        """Count evidence references"""
        evidence_words = ["evidence", "proof", "data", "research", "studies"]
        return sum(1 for word in evidence_words if word in response_text.lower())

    def _count_logical_connectors(self, response_text: str) -> int:
        """Count logical connectors"""
        connectors = ["therefore", "because", "thus", "however", "moreover", "furthermore"]
        return sum(1 for connector in connectors if connector in response_text.lower())

    def _calculate_complexity_score(self, response_text: str) -> float:
        """Calculate complexity score"""
        sentences = response_text.split(".")
        avg_sentence_length = sum(len(s.split()) for s in sentences) / max(1, len(sentences))
        return min(10, avg_sentence_length / 10)

    def _calculate_clarity_score(self, response_text: str) -> float:
        """Calculate clarity score"""
        # Simple clarity measure based on common words vs complex words
        words = response_text.lower().split()
        common_words = ["the", "and", "of", "to", "in", "is", "that", "for", "as", "with"]
        clarity_ratio = sum(1 for word in words if word in common_words) / max(1, len(words))
        return min(10, clarity_ratio * 10)

    def _calculate_novelty_score(self, response_text: str) -> float:
        """Calculate novelty score"""
        # Simple novelty measure based on unique words
        words = response_text.lower().split()
        unique_words = len(set(words))
        novelty_ratio = unique_words / max(1, len(words))
        return min(10, novelty_ratio * 10)

    def _calculate_overall_quality(self, response_text: str) -> float:
        """Calculate overall quality score"""
        quality = self._calculate_quality_score(response_text)
        coherence = self._calculate_coherence_score(response_text)
        clarity = self._calculate_clarity_score(response_text)
        return (quality + coherence + clarity) / 3

    def _calculate_response_diversity(self, blob_store: dict) -> float:
        """Calculate response diversity"""
        responses = []
        for blob_data in blob_store.values():
            if "result" in blob_data and "response" in blob_data["result"]:
                responses.append(blob_data["result"]["response"])

        if len(responses) <= 1:
            return 0.0

        # Simple diversity measure
        unique_words = set()
        total_words = 0
        for response in responses:
            words = response.lower().split()
            unique_words.update(words)
            total_words += len(words)

        return len(unique_words) / max(1, total_words)

    def _calculate_processing_complexity(self, blob_store: dict) -> float:
        """Calculate processing complexity"""
        return len(blob_store) * 0.1  # Simple complexity measure

    def _calculate_memory_relevance(self, memories: list) -> float:
        """Calculate memory relevance"""
        if not memories:
            return 0.0
        return min(10, len(memories) * 0.5)

    def _calculate_memory_diversity(self, memories: list) -> float:
        """Calculate memory diversity"""
        if not memories:
            return 0.0
        return min(10, len(set(str(m) for m in memories)) / max(1, len(memories)) * 10)

    def _calculate_memory_recency(self, memories: list) -> float:
        """Calculate memory recency"""
        return 5.0  # Placeholder - would need timestamp analysis

    def _calculate_memory_utilization(self, memories: list, blob_data: dict) -> float:
        """Calculate memory utilization"""
        if not memories:
            return 0.0
        return min(10, len(memories) * 0.3)

    def save_to_csv(self, data: list, filename: str):
        """Save data to CSV file"""
        if not data:
            print(f"No data to save for {filename}")
            return

        with open(filename, "w", newline="", encoding="utf-8") as csvfile:
            if data:
                writer = csv.DictWriter(csvfile, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)

        print(f"Saved {len(data)} rows to {filename}")

    def extract_all_enhanced_data(self):
        """Extract all enhanced data"""
        print("Loading data...")
        self.load_data()

        print("Extracting detailed responses...")
        detailed_responses = self.extract_detailed_responses()
        self.save_to_csv(detailed_responses, "detailed_responses.csv")

        print("Extracting debate dynamics...")
        debate_dynamics = self.extract_debate_dynamics()
        self.save_to_csv(debate_dynamics, "debate_dynamics.csv")

        print("Extracting convergence analysis...")
        convergence_analysis = self.extract_convergence_analysis()
        self.save_to_csv(convergence_analysis, "convergence_analysis.csv")

        print("Extracting quality metrics...")
        quality_metrics = self.extract_quality_metrics()
        self.save_to_csv(quality_metrics, "quality_metrics.csv")

        print("Extracting execution timeline...")
        execution_timeline = self.extract_execution_timeline()
        self.save_to_csv(execution_timeline, "execution_timeline.csv")

        print("Extracting memory usage...")
        memory_usage = self.extract_memory_usage()
        self.save_to_csv(memory_usage, "memory_usage.csv")

        print("Enhanced comprehensive extraction complete!")


def main():
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

    extractor = EnhancedOrkaExtractor(file_paths)
    extractor.extract_all_enhanced_data()


if __name__ == "__main__":
    main()
