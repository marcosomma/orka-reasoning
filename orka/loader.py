"""Configuration loader module for OrKa."""

import logging
import yaml
from typing import Any, Dict, List, cast

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Load and validate configuration files.

    This class handles loading and basic validation of YAML configuration files
    for the OrKa system.
    """

    def __init__(self, path: str) -> None:
        """Initialize the config loader.

        Args:
            path: Path to the configuration file.
        """
        self.path = path

    def load(self) -> Dict[str, Any]:
        """Load the configuration file.

        Returns:
            The loaded YAML configuration.

        Raises:
            FileNotFoundError: If the configuration file does not exist.
            yaml.YAMLError: If the configuration file is invalid YAML.
        """
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                config = cast(Dict[str, Any], yaml.safe_load(f))
            return config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return cast(Dict[str, Any], {})

    def get_orchestrator(self) -> Dict[str, Any]:
        """Get the orchestrator configuration section.

        Returns:
            The orchestrator configuration dictionary.
        """
        config = self.load()
        return cast(Dict[str, Any], config.get("orchestrator", {}))

    def get_agents(self) -> List[Dict[str, Any]]:
        """Get the agents configuration section.

        Returns:
            The list of agent configurations.
        """
        config = self.load()
        return cast(List[Dict[str, Any]], config.get("agents", []))

    def validate(self) -> bool:
        """Validate the configuration.

        Returns:
            True if the configuration is valid.

        Raises:
            ValueError: If the configuration is invalid.
        """
        config = self.load()
        if "orchestrator" not in config:
            raise ValueError("Missing 'orchestrator' section in config")
        if "agents" not in config:
            raise ValueError("Missing 'agents' section in config")
        if not isinstance(config["agents"], list):
            raise ValueError("'agents' should be a list")
        return True
