# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
# License: Apache 2.0

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from time import time
from uuid import uuid4

from ..error_handling import ErrorReporter, ErrorTelemetry
from ..execution import AgentExecutor, ParallelExecutor
from ..fork_group_manager import ForkGroupManager, SimpleForkGroupManager
from ..loader import YAMLLoader
from ..memory_logger import create_memory_logger
from ..reporting import MetaReportGenerator
from ..utils.common_utils import CommonUtils
from .agent_manager import AgentManager

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    The Orchestrator is the core engine that loads a YAML configuration,
    instantiates agents and nodes, and manages the execution of the reasoning workflow.
    It supports parallelism, dynamic routing, and full trace logging.
    """

    def __init__(self, config_path):
        """
        Initialize the Orchestrator with a YAML config file.
        Loads orchestrator and agent configs, sets up memory and fork management.
        """
        self.loader = YAMLLoader(config_path)
        self.loader.validate()

        self.orchestrator_cfg = self.loader.get_orchestrator()
        self.agent_cfgs = self.loader.get_agents()

        # Configure memory backend
        memory_backend = os.getenv("ORKA_MEMORY_BACKEND", "redis").lower()

        # Get debug flag from orchestrator config or environment
        debug_keep_previous_outputs = self.orchestrator_cfg.get("debug", {}).get(
            "keep_previous_outputs",
            False,
        )
        debug_keep_previous_outputs = (
            debug_keep_previous_outputs
            or os.getenv("ORKA_DEBUG_KEEP_PREVIOUS_OUTPUTS", "false").lower() == "true"
        )

        if memory_backend == "kafka":
            self.memory = create_memory_logger(
                backend="kafka",
                bootstrap_servers=os.getenv(
                    "KAFKA_BOOTSTRAP_SERVERS",
                    "localhost:9092",
                ),
                topic_prefix=os.getenv("KAFKA_TOPIC_PREFIX", "orka-memory"),
                debug_keep_previous_outputs=debug_keep_previous_outputs,
            )
            # For Kafka, we'll use a simple in-memory fork manager since Kafka doesn't have Redis-like operations
            self.fork_manager = SimpleForkGroupManager()
        else:
            self.memory = create_memory_logger(
                backend="redis",
                redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
                debug_keep_previous_outputs=debug_keep_previous_outputs,
            )
            # For Redis, use the existing Redis-based fork manager
            self.fork_manager = ForkGroupManager(self.memory.redis)

        self.queue = self.orchestrator_cfg["agents"][:]  # Initial agent execution queue
        self.run_id = str(uuid4())  # Unique run/session ID
        self.step_index = 0  # Step counter for traceability

        # Initialize modular components
        self.error_telemetry = ErrorTelemetry(self.run_id)
        self.error_reporter = ErrorReporter(self.run_id, self.memory)
        self.agent_manager = AgentManager(self.memory)
        self.meta_report_generator = MetaReportGenerator()

        # Initialize agents using the agent manager
        self.agents = self.agent_manager.init_agents(self.agent_cfgs)

        # Initialize components that need access to agents
        self.agent_executor = AgentExecutor(self.fork_manager, self.memory, self.queue, self.agents)
        self.parallel_executor = ParallelExecutor(self.agent_manager, self.memory)

        print(self.orchestrator_cfg)
        print(self.agent_cfgs)

    def enqueue_fork(self, agent_ids, fork_group_id):
        """
        Add agent IDs to the execution queue (used for forked/parallel execution).
        """
        self.queue.extend(agent_ids)  # Add to queue keeping order

    async def run(self, input_data):
        """
        Main execution loop for the orchestrator with comprehensive error handling.
        Always returns a JSON report, even on failure, for debugging purposes.
        """
        logs = []

        try:
            return await self._run_with_comprehensive_error_handling(input_data, logs)
        except Exception as critical_error:
            # Critical failure - save everything we have so far
            self.error_telemetry.record_error(
                "critical_failure",
                "orchestrator",
                f"Critical orchestrator failure: {critical_error}",
                critical_error,
                severity="critical",
            )

            print(f"💥 [ORKA-CRITICAL] Orchestrator failed: {critical_error}")

            # Generate meta report even on failure
            try:
                meta_report = self.meta_report_generator.generate_meta_report(logs)
            except Exception as e:
                meta_report = {"error": f"Failed to generate meta report: {e}"}

            error_report_path = self.error_reporter.save_error_report(
                logs,
                self.error_telemetry.get_telemetry_data(),
                meta_report,
                critical_error,
            )

            # Try to cleanup memory backend
            try:
                self.memory.close()
            except Exception as cleanup_error:
                print(f"⚠️ Failed to cleanup memory backend: {cleanup_error}")

            # Return error report for debugging instead of raising
            return {
                "status": "critical_failure",
                "error": str(critical_error),
                "error_report_path": error_report_path,
                "logs_captured": len(logs),
                "error_telemetry": self.error_telemetry.get_telemetry_data(),
            }

    async def _run_with_comprehensive_error_handling(self, input_data, logs):
        """
        Main execution loop with comprehensive error handling wrapper.
        """
        # Use self.queue which can be modified by enqueue_fork
        queue = self.queue

        while queue:
            agent_id = queue.pop(0)

            try:
                agent = self.agents[agent_id]
                agent_type = self._get_agent_type_string(agent)
                self.step_index += 1

                # Build payload for the agent: current input and all previous outputs
                payload = {
                    "input": input_data,
                    "previous_outputs": CommonUtils.build_previous_outputs(logs),
                }
                freezed_payload = json.dumps(
                    payload,
                )  # Freeze the payload as a string for logging/debug
                print(
                    f"{datetime.now()} > [ORKA] {self.step_index} > Running agent '{agent_id}' of type '{agent_type}', payload: {freezed_payload}",
                )
                log_entry = {
                    "agent_id": agent_id,
                    "event_type": agent.__class__.__name__,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

                start_time = time()

                # Attempt to run agent with retry logic
                max_retries = 3
                retry_count = 0
                agent_result = None

                while retry_count <= max_retries:
                    try:
                        agent_result = await self.agent_executor.execute_single_agent(
                            agent_id,
                            agent,
                            agent_type,
                            payload,
                            input_data,
                            queue,
                            logs,
                            self.step_index,
                        )

                        # If we had retries, record partial success
                        if retry_count > 0:
                            self.error_telemetry.record_partial_success(agent_id, retry_count)

                        # Handle waiting status - re-queue the agent
                        if isinstance(agent_result, dict) and agent_result.get("status") in [
                            "waiting",
                            "timeout",
                        ]:
                            if agent_result.get("status") == "waiting":
                                queue.append(agent_id)  # Re-queue for later
                            # For these statuses, we should continue to the next agent in queue
                            continue

                        break  # Success - exit retry loop

                    except Exception as agent_error:
                        retry_count += 1
                        self.error_telemetry.record_retry(agent_id)
                        self.error_telemetry.record_error(
                            "agent_execution",
                            agent_id,
                            f"Attempt {retry_count} failed: {agent_error}",
                            agent_error,
                            step=self.step_index,
                            recovery_action="retry" if retry_count <= max_retries else "skip",
                        )

                        if retry_count <= max_retries:
                            print(
                                f"🔄 [ORKA-RETRY] Agent {agent_id} failed, retrying ({retry_count}/{max_retries})",
                            )
                            await asyncio.sleep(1)  # Brief delay before retry
                        else:
                            print(
                                f"❌ [ORKA-SKIP] Agent {agent_id} failed {max_retries} times, skipping",
                            )
                            # Create a failure result
                            agent_result = {
                                "status": "failed",
                                "error": str(agent_error),
                                "retries_attempted": retry_count - 1,
                            }
                            break

                # Process the result (success or failure)
                if agent_result is not None:
                    # Log the result and timing for this step
                    duration = round(time() - start_time, 4)
                    payload_out = {"input": input_data, "result": agent_result}
                    payload_out["previous_outputs"] = payload["previous_outputs"]
                    log_entry["duration"] = duration

                    # Extract LLM metrics if present (even from failed agents)
                    try:
                        llm_metrics = CommonUtils.extract_llm_metrics(agent, agent_result)
                        if llm_metrics:
                            log_entry["llm_metrics"] = llm_metrics
                    except Exception as metrics_error:
                        self.error_telemetry.record_error(
                            "metrics_extraction",
                            agent_id,
                            f"Failed to extract metrics: {metrics_error}",
                            metrics_error,
                            step=self.step_index,
                            recovery_action="continue",
                        )

                    log_entry["payload"] = payload_out
                    logs.append(log_entry)

                    # Save to memory even if agent failed
                    try:
                        if agent_type != "forknode":
                            self.memory.log(
                                agent_id,
                                agent.__class__.__name__,
                                payload_out,
                                step=self.step_index,
                                run_id=self.run_id,
                            )
                    except Exception as memory_error:
                        self.error_telemetry.record_error(
                            "memory_logging",
                            agent_id,
                            f"Failed to log to memory: {memory_error}",
                            memory_error,
                            step=self.step_index,
                            recovery_action="continue",
                        )

                    print(
                        f"{datetime.now()} > [ORKA] {self.step_index} > Agent '{agent_id}' returned: {agent_result}",
                    )

            except Exception as step_error:
                # Catch-all for any other step-level errors
                self.error_telemetry.record_error(
                    "step_execution",
                    agent_id,
                    f"Step execution failed: {step_error}",
                    step_error,
                    step=self.step_index,
                    recovery_action="continue",
                )
                print(
                    f"⚠️ [ORKA-STEP-ERROR] Step {self.step_index} failed for {agent_id}: {step_error}",
                )
                continue  # Continue to next agent

        # Generate meta report with aggregated metrics
        meta_report = self.meta_report_generator.generate_meta_report(logs)

        # Save logs to file at the end of the run
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir = os.getenv("ORKA_LOG_DIR", "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, f"orka_trace_{timestamp}.json")

        # Store meta report in memory for saving
        meta_report_entry = {
            "agent_id": "meta_report",
            "event_type": "MetaReport",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "meta_report": meta_report,
                "run_id": self.run_id,
                "timestamp": timestamp,
            },
        }
        self.memory.memory.append(meta_report_entry)

        # Save to memory backend
        self.memory.save_to_file(log_path)

        # Cleanup memory backend resources to prevent hanging
        try:
            self.memory.close()
        except Exception as e:
            print(f"Warning: Failed to cleanly close memory backend: {e!s}")

        # Print meta report summary
        print("\n" + "=" * 50)
        print("ORKA EXECUTION META REPORT")
        print("=" * 50)
        print(f"Total Execution Time: {meta_report['total_duration']:.3f}s")
        print(f"Total LLM Calls: {meta_report['total_llm_calls']}")
        print(f"Total Tokens: {meta_report['total_tokens']}")
        print(f"Total Cost: ${meta_report['total_cost_usd']:.6f}")
        print(f"Average Latency: {meta_report['avg_latency_ms']:.2f}ms")
        print("=" * 50)

        return logs

    def _get_agent_type_string(self, agent):
        """
        Get the agent type string for an agent instance.

        Args:
            agent: Agent instance

        Returns:
            str: Agent type string
        """
        return self.agent_executor.get_agent_type_string(agent)

    async def run_parallel_agents(
        self,
        agent_ids,
        fork_group_id,
        input_data,
        previous_outputs,
    ):
        """
        Run multiple branches in parallel, with agents within each branch running sequentially.
        Returns a list of log entries for each forked agent.
        """
        return await self.parallel_executor.run_parallel_agents(
            agent_ids,
            fork_group_id,
            input_data,
            previous_outputs,
            self.agents,
            self.run_id,
            self.step_index,
        )
