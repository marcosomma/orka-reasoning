.. OrKa documentation master file

Welcome to OrKa's Documentation!
=================================

OrKa is a powerful AI orchestration framework that enables the creation of complex, multi-agent AI workflows with sophisticated memory management, dynamic routing, and real-time collaboration capabilities.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   modules

Features
========

* **Multi-Agent Architecture**: Support for various LLM providers including OpenAI, Local LLMs, and custom agents
* **Advanced Memory System**: RedisStack-based vector search with HNSW indexing for 100x faster retrieval
* **Dynamic Workflow Control**: Fork/Join patterns, loops, conditional routing, and failover mechanisms
* **Real-time Collaboration**: Agent societies with memory sharing and dynamic interaction
* **Observability**: Comprehensive logging, metrics, and TUI interface for monitoring
* **Production Ready**: Docker support, scalable backends (Kafka + Redis), and robust error handling

Quick Start
===========

1. **Installation**::

    pip install orka-reasoning

2. **Start the backend**::

    python -m orka.orka_start

3. **Run a workflow**::

    python -m orka.orka_cli run your_workflow.yml

Architecture Overview
====================

OrKa consists of several key components:

* **Agents**: Intelligent processing units (LLM agents, local agents, validation agents)
* **Nodes**: Workflow building blocks (memory, routing, control flow)
* **Orchestrator**: Execution engine with advanced scheduling and error handling
* **Memory System**: Persistent storage with vector search capabilities
* **CLI & TUI**: Command-line and terminal interfaces for management

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
