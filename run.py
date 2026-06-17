#!/usr/bin/env python3
"""Convenience launcher for MathAssistant.

Run from the project root:
    python run.py
    python run.py --api-key sk-xxx --model deepseek-chat

Or set DEEPSEEK_API_KEY environment variable first:
    export DEEPSEEK_API_KEY=sk-xxx
    python run.py
"""

import sys
import os

# Force UTF-8 output on Windows (required for emoji rendering in Rich)
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from math_assistant.main import main

if __name__ == "__main__":
    main()
