#!/usr/bin/env python3
"""
OrKa Basic Redis Backend Starter
===============================

Starts OrKa with BASIC Redis backend (no vector search).
For vector search capabilities, use the default RedisStack backend.
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# ✅ CRITICAL: Force basic Redis (not RedisStack)
os.environ["ORKA_MEMORY_BACKEND"] = "redis"
os.environ["ORKA_FORCE_BASIC_REDIS"] = "true"  # ← ADD: Flag to force basic Redis

print("🔧 Starting OrKa with BASIC Redis (no vector search)")
print("💡 For vector search, use: python -m orka.orka_start")
print("📊 Backend: Basic Redis (streams only)")

# Import and run the main function
if __name__ == "__main__":
    import asyncio

    from orka.orka_start import main

    asyncio.run(main())
