<p align="center">

<img src="https://orkacore.com/assets/orka_logo_white.png" alt="OrKa Logo" style="border-radius: 25px; width: 400px; height:400px" />

[![GitHub Tag](https://img.shields.io/github/v/tag/marcosomma/orka-reasoning?color=blue)](https://github.com/marcosomma/orka-reasoning/tags)
[![PyPI - License](https://img.shields.io/pypi/l/orka-reasoning?color=blue)](https://pypi.org/project/orka-reasoning/)

[![Unit Tests](https://github.com/marcosomma/orka-reasoning/actions/workflows/tests.yml/badge.svg)](https://github.com/marcosomma/orka-reasoning/actions/workflows/tests.yml) [![Lint](https://github.com/marcosomma/orka-reasoning/actions/workflows/lint.yml/badge.svg)](https://github.com/marcosomma/orka-reasoning/actions/workflows/lint.yml)

<!-- [![codecov](https://img.shields.io/badge/codecov-76.97%25-yellow?&amp;logo=codecov)](https://codecov.io/gh/marcosomma/orka-reasoning) -->
[![codecov](https://codecov.io/github/marcosomma/orka-reasoning/branch/master/graph/badge.svg?token=V91X4WGBBZ)](https://codecov.io/github/marcosomma/orka-reasoning)
[![orka-reasoning](https://snyk.io/advisor/python/orka-reasoning/badge.svg)](https://snyk.io/advisor/python/orka-reasoning)

[![PyPi](https://img.shields.io/badge/pypi-%23ececec.svg?style=for-the-badge&amp;logo=pypi&amp;logoColor=1f73b7)](https://pypi.org/project/orka-reasoning/)[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&amp;logo=docker&amp;logoColor=white)](https://hub.docker.com/r/marcosomma/orka-ui)[![Documentation](https://img.shields.io/badge/Docs-blue?style=for-the-badge&amp;logo=googledocs&amp;logoColor=%23fff&amp;link=https%3A%2F%2Forkacore.com%2Fdocs%2Findex.html)](https://orkacore.com/docs/index.html)

[![orkacore](https://img.shields.io/badge/orkacore-.com-green?labelColor=blue&amp;style=for-the-badge&amp;link=https://orkacore.com/)](https://orkacore.com/)


[![Pepy Total Downloads](https://img.shields.io/pepy/dt/orka-reasoning?style=for-the-badge&amp;label=Downloads%20from%20April%202025&amp;color=blue&amp;link=https%3A%2F%2Fpiptrends.com%2Fpackage%2Forka-reasoning)](https://clickpy.clickhouse.com/dashboard/orka-reasoning)
</p>

## Maintainer note

People have been reaching out to me lately about Orka-reasoning.

I stopped development last month. Not because I lost interest, and not because I changed my mind about orchestration being the real key. I did not.

Orka was never meant to be a product. It was mostly a playground for me.

2025 was a hard year professionally. I saw the weaknesses of AI demos in real life. I saw the lack of scalability, the overuse of single-agent patterns, and often no real agent design at all. The prompt-and-go strategy worked for demos, but it was not scalable.

That is where Orka came from.

My first commit was just a small POC with two agents processing one input in a linear flow. From there, I added routing, branching, loops, and more. I built it in public because I wanted to show that there was a better path.

Some people engaged from the beginning. Others arrived later. Over the year, I saw around 50k downloads across GitHub and PyPI. Some people came back with feedback. Some contributed. Many criticized it. All of that helped.

Orka kept growing and became a sort of personal AI ecosystem for me. A place where I could build agentic flows with no boundaries, and where critical thinking was part of the pipeline before producing a final output.

It was fun.

Then, slowly, I became a maintainer.

The pressure from download growth started creating expectations. I did not want to release new versions without testing properly, checking backward compatibility, and making sure things were stable. That made me slower, and it also tied me to a narrower problem than the one I actually wanted to explore.

Then 2026 arrived, and more people started catching up with the limitations of AI demos. Investors began asking for real results, not just flashy prototypes. Many products had to rewrite themselves completely. They learned, but from a business perspective, many also burned money and are now dealing with expectations that do not match the real cost of AI.

In my view, this is the silent AI pop. The bubble is not exploding loudly. It is slowly deflating and hitting the ground.

So this is the point.

Orka was fun, and I am quite sure it is full of small gold stones if you want to dig. But it was my playground, not a production-ready product, and it will never be.

You are free to fork it, branch it, and build on top of it. But there will be no maintenance from my side.

## Overview
OrKA-reasoning is a open-source, local‑first, YAML‑driven system for composing AI workflows. Define agents and control‑flow in configuration, run them with a single command, and keep everything observable and reproducible.

Think of it as a streamlined, open-source experimental framework with a strong focus on:
- YAML‑first workflows: declarative configs over code > see [YAML Configuration](docs/YAML_CONFIGURATION.md)
- Visual builder and runner (drag‑and‑drop) > see [OrKa UI](docs/orka-ui.md)
- Built‑in memory with vector search and decay > see [Memory System](docs/MEMORY_SYSTEM_GUIDE.md)
- Local and cloud LLM support with cost controls > see [Backends](docs/README_BACKENDS.md)
- Rich control flow (router, fork/join, loop, failover, plan validation) > see [Agents & Nodes](docs/AGENT_NODE_TOOL_INDEX.md)
- Path discovery with GraphScout (beta) > see [GraphScout](docs/GRAPH_SCOUT_AGENT.md)
- Structured JSON inputs for complex data > see [JSON Inputs](docs/JSON_INPUTS.md)
- Observability and tracing > see [Observability](docs/observability.md)
- Testing guidance and examples > see [Testing Guide](docs/TESTING.md)

## Get started

- Quickstart: [docs/quickstart.md](docs/quickstart.md)
- Documentation index: [docs/index.md](docs/index.md)
- Examples: [examples/](examples)

## Community

- Issues & feature requests: https://github.com/marcosomma/orka-reasoning/issues
- Contributing guide: [CONTRIBUTING.md](CONTRIBUTING.md)

## License

Apache 2.0 — see [LICENSE](LICENSE)
