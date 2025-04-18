# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka
#
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://creativecommons.org/licenses/by-nc/4.0/legalcode
# For commercial use, contact: marcosomma.work@gmail.com
# 
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="orka-reasoning",
    version="0.1.2",
    author="Marco Somma",
    author_email="marcosomma.work@gmail.com",
    description="OrKa: Modular orchestration for agent-based cognition",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/marcosomma/orka",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "redis",
        "pyyaml",
        "litellm",
        "jinja2",
        "google-api-python-client",
        "duckduckgo-search",
        "python-dotenv",
        "openai",
        "async-timeout",
    ],
    extras_require={
        "dev": ["pytest", "coverage", "pytest-cov"]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: Other/Proprietary License",  # Use this for CC BY-NC
        "Operating System :: OS Independent"
    ],
    python_requires=">=3.8",
)
