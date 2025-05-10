import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from ..contracts import Context, Output, Registry
from ..utils.concurrency import ConcurrencyManager

logger = logging.getLogger(__name__)


class BaseAgent:
    """Base class for all agents."""

    def __init__(
        self,
        agent_id: str,
        registry: Registry,
        timeout: Optional[float] = 30.0,
        max_concurrency: int = 10,
    ):
        self.agent_id = agent_id
        self.registry = registry
        self.timeout = timeout
        self.concurrency = ConcurrencyManager(max_concurrency=max_concurrency)
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the agent and its resources."""
        if self._initialized:
            return
        self._initialized = True

    async def run(self, ctx: Context) -> Output:
        """Run the agent with the given context."""
        if not self._initialized:
            await self.initialize()

        # Add trace information if not present
        if "trace_id" not in ctx:
            ctx["trace_id"] = str(uuid.uuid4())
        if "timestamp" not in ctx:
            ctx["timestamp"] = datetime.now()

        try:
            # Use concurrency manager to run the agent
            result = await self.concurrency.run_with_timeout(
                self._run_impl, self.timeout, ctx
            )
            return Output(
                result=result,
                status="success",
                error=None,
                metadata={"agent_id": self.agent_id},
            )
        except Exception as e:
            logger.error(f"Agent {self.agent_id} failed: {str(e)}")
            return Output(
                result=None,
                status="error",
                error=str(e),
                metadata={"agent_id": self.agent_id},
            )

    async def _run_impl(self, ctx: Context) -> Any:
        """Implementation of the agent's run logic."""
        raise NotImplementedError("Subclasses must implement _run_impl")

    async def cleanup(self) -> None:
        """Clean up agent resources."""
        await self.concurrency.shutdown()
