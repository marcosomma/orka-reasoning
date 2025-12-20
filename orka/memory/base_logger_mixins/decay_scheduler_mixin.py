# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""
Decay Scheduler Mixin
=====================

Methods for managing automatic memory decay scheduling.
"""

import logging
import threading
from typing import Any

logger = logging.getLogger(__name__)


class DecaySchedulerMixin:
    """Mixin providing decay scheduler methods."""

    # Expected from host class
    decay_config: dict[str, Any]
    _decay_thread: threading.Thread | None
    _decay_stop_event: threading.Event

    def _start_decay_scheduler(self):
        """Start the automatic decay scheduler thread."""
        if self._decay_thread is not None:
            return  # Already running

        def decay_scheduler() -> None:
            interval_seconds = self.decay_config.get("check_interval_minutes", 1) * 60
            consecutive_failures = 0
            max_consecutive_failures = 3

            while not self._decay_stop_event.wait(interval_seconds):
                try:
                    self.cleanup_expired_memories()
                    consecutive_failures = 0
                except Exception as e:
                    consecutive_failures += 1
                    logger.error(
                        f"Error during automatic memory decay "
                        f"(failure {consecutive_failures}): {e}"
                    )

                    if consecutive_failures >= max_consecutive_failures:
                        logger.warning(
                            f"Memory decay has failed {consecutive_failures} times. "
                            f"Increasing interval to prevent resource exhaustion."
                        )
                        interval_seconds = min(interval_seconds * 2, 3600)
                        consecutive_failures = 0

        self._decay_thread = threading.Thread(target=decay_scheduler, daemon=True)
        self._decay_thread.start()
        logger.info(
            f"Started automatic memory decay scheduler "
            f"(interval: {self.decay_config['check_interval_minutes']} minutes)"
        )

    def stop_decay_scheduler(self):
        """Stop the automatic decay scheduler."""
        if self._decay_thread is not None:
            self._decay_stop_event.set()
            self._decay_thread.join(timeout=5)
            self._decay_thread = None
            logger.info("Stopped automatic memory decay scheduler")

    def cleanup_expired_memories(self, dry_run: bool = False) -> dict[str, Any]:
        """
        Clean up expired memory entries.

        This is a stub - concrete implementations must override.
        """
        raise NotImplementedError("Subclasses must implement cleanup_expired_memories")

