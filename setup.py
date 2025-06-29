# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-resoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-resoning

from setuptools import find_packages, setup

with open("README.md", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="orka-reasoning",
    version="0.6.6",
    author="Marco Somma",
    author_email="marcosomma.work@gmail.com",
    description="OrKa: Modular orchestration for agent-based cognition",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://orkacore.com",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "redis>=4.5.0",
        "pyyaml>=6.0",
        "litellm>=1.0.0",
        "jinja2>=3.0.0",
        "google-api-python-client>=2.0.0",
        "duckduckgo-search>=3.0.0",
        "python-dotenv>=0.19.0",
        "openai>=1.0.0",
        "async-timeout>=4.0.0",
        "fastapi>=0.68.0",
        "uvicorn>=0.15.0",
        "pydantic>=1.8.0",
        "httpx>=0.24.0",
        "rich>=13.0.0",
        "textual>=0.40.0",
    ],
    extras_require={"dev": ["pytest", "coverage", "pytest-cov"]},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: Other/Proprietary License",  # Use this for CC BY-NC
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "orka-start=orka.orka_start:main",
            "orka=orka.orka_cli:main",
        ],
    },
    package_data={
        "orka": ["docker/*", "docker/**/*", "requirements.txt"],
    },
)
