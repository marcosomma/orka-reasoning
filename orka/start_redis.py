#!/usr/bin/env python3
"""
OrKa Redis Backend Starter
=========================

Simple script to start OrKa with Redis backend.
This is equivalent to running:
    ORKA_MEMORY_BACKEND=redis python -m orka.orka_start
"""

import os
import sys
from pathlib import Path

# Set Redis backend
os.environ["ORKA_MEMORY_BACKEND"] = "redis"

# Import and run the main function
if __name__ == "__main__":
    try:
        import asyncio

        from orka.orka_start import main

        asyncio.run(main())
    except ImportError:
        # Fallback for development environments
        current_dir = Path(__file__).parent
        sys.path.insert(0, str(current_dir))
        import asyncio

        from orka_start import main

        asyncio.run(main())
