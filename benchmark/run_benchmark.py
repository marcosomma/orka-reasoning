#!/usr/bin/env python3
"""
Benchmark Runner for Orka

This script runs questions through the cognitive society workflow and evaluates the answers
against a reference dataset using a simple evaluator workflow.

Usage:
    python run_benchmark.py cognitive_workflow.yml evaluator_workflow.yml test.jsonl
"""

import asyncio
import gc
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, cast

try:
    import numpy as np
    import pandas as pd  # type: ignore
except ImportError:
    print("Required packages not installed. Please install with: pip install pandas numpy")
    sys.exit(1)


class NumpyJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for numpy types."""

    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


from orka.loader import YAMLLoader
from orka.orchestrator import Orchestrator

# Ensure logs directory exists
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            log_dir / f'benchmark_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        ),
    ],
)
logger = logging.getLogger(__name__)


class BenchmarkRunner:
    def __init__(
        self, cognitive_workflow_path: str, evaluator_workflow_path: str, test_data_path: str
    ):
        """
        Initialize the benchmark runner.

        Args:
            cognitive_workflow_path: Path to the cognitive society workflow YAML
            evaluator_workflow_path: Path to the evaluator workflow YAML
            test_data_path: Path to the test dataset JSONL file
        """
        self.cognitive_workflow_path = Path(cognitive_workflow_path)
        self.evaluator_workflow_path = Path(evaluator_workflow_path)
        self.test_data_path = Path(test_data_path)
        self.results: List[Dict[str, Any]] = []
        self.chunk_reports: List[Dict[str, Any]] = []

        # Chunk processing settings
        self.chunk_size = 50

        # Ensure logs directory exists
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)

        # Load workflows
        self.cognitive_orchestrator = Orchestrator(str(self.cognitive_workflow_path))
        self.evaluator_orchestrator = Orchestrator(str(self.evaluator_workflow_path))

    def load_test_data(self) -> List[Dict[str, Any]]:
        """Load test cases from JSONL file."""
        with open(self.test_data_path, "r", encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    async def run_single_test(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single test case through both workflows."""
        try:
            # Extract question and reference answer
            question = test_case["question"]
            reference = test_case["answer"]

            # Run through cognitive society workflow
            logger.info(f"Running cognitive society workflow for question: {question[:100]}...")
            cognitive_result = await self.cognitive_orchestrator.run(question)
            cognitive_result = cast(Dict[str, Any], cognitive_result)

            # Extract Orka's answer from cognitive society result
            if isinstance(cognitive_result, dict):
                orka_answer = cognitive_result.get("final_answer_builder", {}).get("response", "")
                if not orka_answer:
                    # Fallback to last agent if final_answer_builder not found
                    cognitive_loader = YAMLLoader(str(self.cognitive_workflow_path))
                    for agent_id in reversed(cognitive_loader.get_orchestrator().get("agents", [])):
                        if agent_id in cognitive_result:
                            orka_answer = cognitive_result[agent_id].get("response", "")
                            if orka_answer:
                                break
            else:
                # If result is a string, use it directly
                orka_answer = str(cognitive_result)

            # Run through evaluator workflow
            logger.info("Evaluating answers...")
            evaluation_result = await self.evaluator_orchestrator.run(
                {
                    "question": question,
                    "reference_answer": reference,
                    "orka_answer": orka_answer,
                }
            )
            evaluation_result = cast(Dict[str, Any], evaluation_result)

            # Extract evaluation
            if isinstance(evaluation_result, dict):
                evaluation = evaluation_result.get("answer_evaluator", {}).get("response", "")
            else:
                evaluation = str(evaluation_result)

            # Initialize scores
            similarity_score = 0.0
            precision_score = 0.0
            explainability_score = 0.0

            # Parse evaluation results
            try:
                # Try to parse as dictionary first
                if evaluation.startswith("{") and evaluation.endswith("}"):
                    try:
                        # Convert string representation of dict to actual dict
                        eval_dict = eval(evaluation)
                        similarity_score = float(eval_dict.get("SIMILARITY_SCORE", 0.0))
                        precision_score = float(eval_dict.get("PRECISION", 0.0))
                        explainability_score = float(eval_dict.get("EXPLAINABILITY", 0.0))
                        strengths = eval_dict.get("STRENGTHS", ["No strengths provided"])
                        if isinstance(strengths, list):
                            strengths = "\n- " + "\n- ".join(strengths)
                        weaknesses = eval_dict.get("WEAKNESSES", ["No weaknesses provided"])
                        if isinstance(weaknesses, list):
                            weaknesses = "\n- " + "\n- ".join(weaknesses)
                        analysis = eval_dict.get("ANALYSIS", "No analysis provided")
                        return_early = True
                    except Exception as e:
                        logger.warning(f"Failed to parse evaluation as dict: {e}")
                        return_early = False
                else:
                    return_early = False

                if not return_early:
                    # Fallback to line-by-line parsing
                    if "SIMILARITY_SCORE:" not in evaluation:
                        logger.warning("No similarity score found in evaluation")
                        strengths = "No evaluation provided"
                        weaknesses = "No evaluation provided"
                        analysis = evaluation
                    else:
                        parts = evaluation.split("\n")
                        for part in parts:
                            part = part.strip()
                            if "SIMILARITY_SCORE:" in part:
                                similarity_score = float(
                                    part.split("SIMILARITY_SCORE:")[1].strip().split()[0]
                                )
                            elif "PRECISION:" in part:
                                precision_score = float(
                                    part.split("PRECISION:")[1].strip().split()[0]
                                )
                            elif "EXPLAINABILITY:" in part:
                                explainability_score = float(
                                    part.split("EXPLAINABILITY:")[1].strip().split()[0]
                                )

                    # Extract sections more robustly
                    strengths = (
                        evaluation.split("STRENGTHS:")[1].split("WEAKNESSES:")[0].strip()
                        if "STRENGTHS:" in evaluation and "WEAKNESSES:" in evaluation
                        else "No strengths provided"
                    )
                    weaknesses = (
                        evaluation.split("WEAKNESSES:")[1].split("ANALYSIS:")[0].strip()
                        if "WEAKNESSES:" in evaluation and "ANALYSIS:" in evaluation
                        else "No weaknesses provided"
                    )
                    analysis = (
                        evaluation.split("ANALYSIS:")[1].strip()
                        if "ANALYSIS:" in evaluation
                        else evaluation
                    )
            except Exception as e:
                logger.error(f"Failed to parse evaluation result: {e}")
                logger.error(f"Raw evaluation: {evaluation}")
                # Keep initialized scores at 0.0
                strengths = f"Failed to parse: {str(e)}"
                weaknesses = "Failed to parse"
                analysis = evaluation

            # Extract metrics safely
            cognitive_metrics = (
                cognitive_result.get("meta_report", {})
                if isinstance(cognitive_result, dict)
                else {}
            )
            evaluation_metrics = (
                evaluation_result.get("meta_report", {})
                if isinstance(evaluation_result, dict)
                else {}
            )

            return {
                "question": question,
                "reference_answer": reference,
                "orka_answer": orka_answer,
                "similarity_score": similarity_score,
                "precision_score": precision_score,
                "explainability_score": explainability_score,
                "strengths": strengths,
                "weaknesses": weaknesses,
                "analysis": analysis,
                "success": True,
                "error": None,
                "cognitive_metrics": cognitive_metrics,
                "evaluation_metrics": evaluation_metrics,
            }

        except Exception as e:
            logger.error(f"Error processing question: {question}")
            logger.exception(e)
            return {
                "question": question,
                "reference_answer": reference,
                "orka_answer": None,
                "similarity_score": 0.0,
                "precision_score": 0.0,
                "explainability_score": 0.0,
                "analysis": None,
                "success": False,
                "error": str(e),
            }

    async def clear_memory(self) -> None:
        """Clear memory between chunks to prevent memory leaks."""
        # Clear results
        self.results.clear()

        # Force garbage collection
        gc.collect()

        # Reinitialize orchestrators to clear any cached state
        self.cognitive_orchestrator = Orchestrator(str(self.cognitive_workflow_path))
        self.evaluator_orchestrator = Orchestrator(str(self.evaluator_workflow_path))

        logger.info("Memory cleared and orchestrators reinitialized")

    def generate_chunk_report(self, chunk_num: int, start_idx: int, end_idx: int) -> Dict[str, Any]:
        """Generate a report for a single chunk."""
        if not self.results:
            return {}

        # Convert results to DataFrame
        df = pd.DataFrame(self.results)

        # Calculate statistics
        total_cases = len(df)
        successful_cases = df["success"].sum()
        successful_df = df[df["success"]]

        # Handle empty successful_df
        if len(successful_df) > 0:
            average_similarity = successful_df["similarity_score"].mean()
            average_precision = successful_df["precision_score"].mean()
            average_explainability = successful_df["explainability_score"].mean()
        else:
            average_similarity = 0.0
            average_precision = 0.0
            average_explainability = 0.0

        # Generate report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.log_dir / f"benchmark_chunk_{chunk_num}_{timestamp}"

        # Save detailed results
        df.to_csv(f"{report_path}.csv", index=False)

        # Save summary
        summary = {
            "chunk_number": chunk_num,
            "start_index": start_idx,
            "end_index": end_idx,
            "total_cases": total_cases,
            "successful_cases": successful_cases,
            "failed_cases": total_cases - successful_cases,
            "success_rate": successful_cases / total_cases * 100 if total_cases > 0 else 0,
            "average_similarity_score": average_similarity,
            "average_precision_score": average_precision,
            "average_explainability_score": average_explainability,
            "timestamp": timestamp,
        }

        with open(f"{report_path}_summary.json", "w") as f:
            json.dump(summary, f, indent=2, cls=NumpyJSONEncoder)

        # Log summary
        logger.info(f"Chunk {chunk_num} Summary:")
        logger.info(f"Cases {start_idx+1}-{end_idx}: {total_cases} total")
        logger.info(f"Successful cases: {successful_cases}")
        logger.info(f"Failed cases: {total_cases - successful_cases}")
        logger.info(f"Success rate: {summary['success_rate']:.2f}%")
        logger.info(f"Average similarity score: {average_similarity:.3f}")
        logger.info(f"Average precision score: {average_precision:.3f}")
        logger.info(f"Average explainability score: {average_explainability:.3f}")
        logger.info(f"Chunk results saved to: {report_path}.csv")
        logger.info(f"Chunk summary saved to: {report_path}_summary.json")

        return summary

    async def run_benchmark(self) -> None:
        """Run the complete benchmark in chunks."""
        test_cases = self.load_test_data()
        total_cases = len(test_cases)

        logger.info(f"Starting benchmark with {total_cases} test cases")
        logger.info(f"Processing in chunks of {self.chunk_size}")

        # Process in chunks
        for chunk_start in range(0, total_cases, self.chunk_size):
            chunk_end = min(chunk_start + self.chunk_size, total_cases)
            chunk_num = (chunk_start // self.chunk_size) + 1
            chunk_cases = test_cases[chunk_start:chunk_end]

            logger.info(f"Processing chunk {chunk_num} (cases {chunk_start+1}-{chunk_end})")

            # Process chunk
            for i, test_case in enumerate(chunk_cases):
                global_idx = chunk_start + i + 1
                logger.info(f"Processing test case {global_idx}/{total_cases} (chunk {chunk_num})")
                result = await self.run_single_test(test_case)
                self.results.append(result)

                # Log progress
                if result["success"]:
                    logger.info(f"Similarity score: {result['similarity_score']:.2f}")
                else:
                    logger.warning(f"Test case failed: {result['error']}")

            # Generate chunk report
            chunk_summary = self.generate_chunk_report(chunk_num, chunk_start, chunk_end - 1)
            self.chunk_reports.append(chunk_summary)

            # Clear memory for next chunk (except for the last chunk)
            if chunk_end < total_cases:
                await self.clear_memory()
                logger.info(f"Completed chunk {chunk_num}, memory cleared for next chunk")
            else:
                logger.info(f"Completed final chunk {chunk_num}")

    def generate_final_report(self) -> None:
        """Generate a consolidated final report from all chunks."""
        if not self.chunk_reports:
            logger.warning("No chunk reports found to consolidate")
            return

        # Calculate overall statistics from chunk summaries
        total_cases = sum(chunk["total_cases"] for chunk in self.chunk_reports)
        total_successful = sum(chunk["successful_cases"] for chunk in self.chunk_reports)
        total_failed = total_cases - total_successful

        # Calculate weighted averages for scores
        total_similarity = 0.0
        total_precision = 0.0
        total_explainability = 0.0
        successful_chunks = [chunk for chunk in self.chunk_reports if chunk["successful_cases"] > 0]

        if successful_chunks:
            for chunk in successful_chunks:
                weight = chunk["successful_cases"]
                total_similarity += chunk["average_similarity_score"] * weight
                total_precision += chunk["average_precision_score"] * weight
                total_explainability += chunk["average_explainability_score"] * weight

            average_similarity = (
                total_similarity / total_successful if total_successful > 0 else 0.0
            )
            average_precision = total_precision / total_successful if total_successful > 0 else 0.0
            average_explainability = (
                total_explainability / total_successful if total_successful > 0 else 0.0
            )
        else:
            average_similarity = 0.0
            average_precision = 0.0
            average_explainability = 0.0

        # Generate final report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_report_path = self.log_dir / f"benchmark_final_report_{timestamp}"

        # Create detailed summary with chunk information
        final_summary = {
            "total_cases": total_cases,
            "successful_cases": total_successful,
            "failed_cases": total_failed,
            "success_rate": total_successful / total_cases * 100 if total_cases > 0 else 0,
            "average_similarity_score": average_similarity,
            "average_precision_score": average_precision,
            "average_explainability_score": average_explainability,
            "total_chunks": len(self.chunk_reports),
            "chunk_size": self.chunk_size,
            "timestamp": timestamp,
            "chunk_summaries": self.chunk_reports,
        }

        with open(f"{final_report_path}_summary.json", "w") as f:
            json.dump(final_summary, f, indent=2, cls=NumpyJSONEncoder)

        # Log final summary
        logger.info("=" * 60)
        logger.info("FINAL BENCHMARK SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total test cases: {total_cases}")
        logger.info(f"Total chunks processed: {len(self.chunk_reports)}")
        logger.info(f"Successful cases: {total_successful}")
        logger.info(f"Failed cases: {total_failed}")
        logger.info(f"Overall success rate: {final_summary['success_rate']:.2f}%")
        logger.info(f"Overall average similarity score: {average_similarity:.3f}")
        logger.info(f"Overall average precision score: {average_precision:.3f}")
        logger.info(f"Overall average explainability score: {average_explainability:.3f}")
        logger.info(f"Final report saved to: {final_report_path}_summary.json")
        logger.info("=" * 60)


async def main():
    """Main entry point for the benchmark runner."""
    if len(sys.argv) != 4:
        print(
            "Usage: python run_benchmark.py <cognitive_workflow.yml> <evaluator_workflow.yml> <test.jsonl>"
        )
        print("\nExample:")
        print(
            "  python run_benchmark.py examples/cognitive_society_with_memory_local_optimal_deepseek-8b.yml"
        )
        print("                        benchmark/benchmark_evaluator.yml")
        print("                        benchmark/test.jsonl")
        sys.exit(1)

    cognitive_workflow_path = sys.argv[1]
    evaluator_workflow_path = sys.argv[2]
    test_data_path = sys.argv[3]

    runner = BenchmarkRunner(cognitive_workflow_path, evaluator_workflow_path, test_data_path)
    await runner.run_benchmark()
    runner.generate_final_report()


if __name__ == "__main__":
    asyncio.run(main())
