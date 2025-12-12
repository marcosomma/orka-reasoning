# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

"""
OrKa Startup Banner
==================

ASCII art banner displayed when OrKa starts up.
"""

import importlib.metadata
from pathlib import Path

ORKA_BANNER = r"""
⠀⠀⠀⠀⠀⠀⢀⣀⣀⣀⣀⣀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠺⢿⣿⣿⣿⣿⣿⣿⣷⣦⣠⣤⣤⣤⣄⣀⣀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠙⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⣦⣄⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⢀⣴⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠿⠿⠿⣿⣿⣷⣄⠀⠀
⠀⠀⠀⠀⠀⢠⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣀⠀⠀⠀⣀⣿⣿⣿⣆⠀
⠀⠀⠀⠀⢠⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡄
⠀⠀⠀⠀⣾⣿⣿⡿⠋⠁⣀⣠⣬⣽⣿⣿⣿⣿⣿⣿⠿⠿⠿⠿⠿⠿⠿⠿⠟⠁
⠀⠀⠀⢀⣿⣿⡏⢀⣴⣿⠿⠛⠉⠉⠀⢸⣿⣿⠿⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⢸⣿⣿⢠⣾⡟⠁⠀⠀⠀⠀⠀⠈⠉⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⢸⣿⣿⣾⠏⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⣸⣿⣿⣿⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⢠⣾⣿⣿⣿⣿⣿⣷⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⣾⣿⣿⣿⣿⣿⣿⣿⣿⣦⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⢰⣿⡿⠛⠉⠀⠀⠀⠈⠙⠛⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠈⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
--------------------------------------
  ██████╗  ██████╗  ██╗  ██╗  █████╗ 
 ██╔═══██╗ ██╔══██╗ ██║ ██╔╝ ██╔══██╗
 ██║   ██║ ██████╔╝ █████╔╝  ███████║
 ██║   ██║ ██╔══██╗ ██╔═██╗  ██╔══██║
 ╚██████╔╝ ██║  ██║ ██║  ██╗ ██║  ██║
  ╚═════╝  ╚═╝  ╚═╝ ╚═╝  ╚═╝ ╚═╝  ╚═╝
--------------------------------------
"""


def get_version():
    """Get OrKa version from package metadata."""
    try:
        return importlib.metadata.version("orka-reasoning")
    except Exception:
        pass

    # Dev fallback: read version from repo pyproject.toml
    try:
        pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
        if pyproject_path.exists():
            import tomllib

            data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
            version = data.get("project", {}).get("version")
            if isinstance(version, str) and version.strip():
                return version.strip()
    except Exception:
        pass

    return "0.9.11"


def display_banner():
    """Display the OrKa startup banner with version info."""
    version = get_version()
    
    # Rainbow colors: red, yellow, green, cyan, blue, magenta
    colors = [
        "\033[1;31m",  # Red
        "\033[1;33m",  # Yellow
        "\033[1;32m",  # Green
        "\033[1;36m",  # Cyan
        "\033[1;34m",  # Blue
        "\033[1;35m",  # Magenta
    ]
    reset = "\033[0m"
    
    # Print banner with rainbow effect (cycle through colors per line)
    lines = ORKA_BANNER.split('\n')
    for i, line in enumerate(lines):
        color = colors[i % len(colors)]
        print(color + line + reset)
    print(f"\033[1;35m  [Or]chestrator [K]it [A]gents\033[0m")  # Magenta
    print("\033[0;90m======================================\033[0m")  # Gray
    print(f"\033[1;33m  • 🧠 Local-first \033[0m")  # Yellow
    print(f"\033[1;33m  • ⚡ YAML-Definition \033[0m")  # Yellow
    print(f"\033[1;33m  • 🎯 Intelligent Routing\033[0m")  # Yellow
    print(f"\033[1;33m  • 🔄 Built for Reasoning\033[0m")  # Yellow
    print("\033[0;90m======================================\033[0m")  # Gray
    print(f"\033[1;34m  By: @marcosomma\033[0m")  # Green
    print(f"\033[1;32m  GitHub: https://github.com/marcosomma/orka-reasoning\033[0m")  # Blue
    print(f"\033[1;37m  Version: v{version}\033[0m")  # White bold
    print(f"\033[1;31m  License: Apache 2.0\033[0m")  # Red
    print("\033[0;90m======================================\033[0m")  # Gray
