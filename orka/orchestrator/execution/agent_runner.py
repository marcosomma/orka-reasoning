# OrKa: Orchestrator Kit Agents
# by Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
#
# Attribution would be appreciated: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

import asyncio
import inspect
import logging
from concurrent.futures import ThreadPoolExecutor
from time import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class AgentRunner:
    """AgentRunner executes individual agents and branches.

    This is a port of ExecutionEngine._run_agent_async, _run_branch_async and
    _run_branch_with_retry. It keeps behavior identical while allowing easier
    testing and future refactors.
    """

    def __init__(self, orchestrator):
        self.orchestrator = orchestrator

    async def run_agent_async(
        self,
        agent_id: str,
        input_data: Any,
        previous_outputs: Dict[str, Any],
        full_payload: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, Any]:
        """Run a single agent asynchronously, returning (agent_id, result)."""
        agent = self.orchestrator.agents[agent_id]

        payload = {"input": input_data, "previous_outputs": previous_outputs}

        if full_payload and "orchestrator" in full_payload:
            payload["orchestrator"] = full_payload["orchestrator"]
            logger.debug(f"- Agent '{agent_id}' inherited orchestrator context from full_payload")

        # Inherit orchestrator-level structured output defaults when available
        try:
            orchestrator_cfg = getattr(self.orchestrator, "orchestrator_cfg", {})
            so_defaults = orchestrator_cfg.get("structured_output_defaults") if isinstance(orchestrator_cfg, dict) else None
            if isinstance(so_defaults, dict) and so_defaults:
                payload["structured_output_defaults"] = so_defaults
        except Exception:
            # Ignore if not available
            pass

        if isinstance(input_data, dict):
            if "loop_number" in input_data:
                payload["loop_number"] = input_data["loop_number"]
            if "past_loops_metadata" in input_data:
                payload["past_loops_metadata"] = input_data["past_loops_metadata"]

        # Prompt rendering if applicable
        agent_prompt = None
        if hasattr(agent, "prompt") and agent.prompt:
            agent_prompt = str(agent.prompt) if not isinstance(agent.prompt, str) else agent.prompt
        elif hasattr(agent, "llm_agent") and hasattr(agent.llm_agent, "prompt") and agent.llm_agent.prompt:
            agent_prompt = (
                str(agent.llm_agent.prompt) if not isinstance(agent.llm_agent.prompt, str) else agent.llm_agent.prompt
            )

        if agent_prompt:
            try:
                formatted_prompt = self.orchestrator.render_template(agent_prompt, payload)
                payload["formatted_prompt"] = formatted_prompt
            except Exception as e:
                logger.error(f"Failed to render prompt for agent '{agent_id}': {e}")
                payload["formatted_prompt"] = agent_prompt if agent_prompt else ""
                payload["template_error"] = str(e)

        run_method = agent.run
        sig = inspect.signature(run_method)
        needs_orchestrator = len(sig.parameters) > 1
        is_async = inspect.iscoroutinefunction(run_method)

        logger.debug(f"- Agent '{agent_id}' run method signature: {sig}")
        logger.debug(f"- Agent '{agent_id}' needs_orchestrator: {needs_orchestrator}")
        logger.debug(f"- Agent '{agent_id}' is_async: {is_async}")

        try:
            if needs_orchestrator:
                context_with_orchestrator = {**payload, "orchestrator": self.orchestrator}
                result = run_method(context_with_orchestrator)
                if is_async or asyncio.iscoroutine(result):
                    result = await result
            elif is_async:
                result = await run_method(payload)
            else:
                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor() as pool:
                    result = await loop.run_in_executor(pool, run_method, payload)

            return agent_id, result

        except Exception as e:
            logger.error(f"Failed to execute agent '{agent_id}': {e}")
            raise

    async def run_branch_async(self, branch_agents: List[str], input_data: Any, previous_outputs: Dict[str, Any]) -> Dict[str, Any]:
        branch_results: Dict[str, Any] = {}
        for agent_id in branch_agents:
            _, result = await self.run_agent_async(agent_id, input_data, previous_outputs, full_payload=None)
            branch_results[agent_id] = result
            previous_outputs = {**previous_outputs, **branch_results}
        return branch_results

    async def run_branch_with_retry(
        self,
        branch_agents: List[str],
        input_data: Any,
        previous_outputs: Dict[str, Any],
        max_retries: int = 2,
        retry_delay: float = 1.0,
    ) -> Dict[str, Any]:
        last_exception = None
        for attempt in range(max_retries + 1):
            try:
                result = await self.run_branch_async(branch_agents, input_data, previous_outputs)
                if attempt > 0:
                    logger.info(f"Branch {branch_agents} succeeded on retry {attempt}")
                return result
            except Exception as e:
                last_exception = e
                if attempt < max_retries:
                    delay = retry_delay * (2**attempt)
                    logger.warning(
                        f"Branch {branch_agents} failed (attempt {attempt + 1}/{max_retries + 1}): {type(e).__name__}: {e}. Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Branch {branch_agents} failed after {max_retries + 1} attempts: {type(e).__name__}: {e}"
                    )
        raise last_exception  # type: ignore
