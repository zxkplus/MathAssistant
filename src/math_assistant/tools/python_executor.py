"""Python code execution tool for MathAssistant.

Executes Python code in a subprocess with timeout protection.
Provides a sandboxed environment for sympy, numpy, and matplotlib.
"""

import ast
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from langchain.tools import tool
from pydantic import BaseModel, Field


class PythonCodeInput(BaseModel):
    code: str = Field(description=(
        "Python code to execute. You can import and use: sympy (symbolic math), "
        "numpy (numerical computation), matplotlib (visualization charts). "
        "Use print() to output results. For charts, save with "
        "plt.savefig('images/chart_name.png') and print the file path."
    ))


# Prologue injected before user code to set up imports and chart settings
_CODE_PROLOGUE = """\
import os
os.environ['MPLBACKEND'] = 'Agg'
import matplotlib
matplotlib.use('Agg')
import sympy as sp
import numpy as np
import matplotlib.pyplot as plt
import math
import json
from sympy import symbols, Eq, solve, diff, integrate, limit, simplify, expand, factor, Matrix, sin, cos, tan, log, exp, sqrt, pi, oo
# User code starts below
"""


def _build_execution_script(code: str, image_dir: str) -> str:
    """Build the full Python script with prologue and image directory setup."""
    # Auto-print: if the last statement is a bare expression (like `solutions`
    # or `x**2`), wrap it with print() so the tool returns visible output.
    try:
        tree = ast.parse(code)
        if tree.body and isinstance(tree.body[-1], ast.Expr):
            # Extract the expression and replace with a print call
            last_expr = tree.body[-1]
            # Use ast.unparse (Python 3.9+) to get the expression source
            expr_src = ast.unparse(last_expr.value)
            # Replace the last line: remove the original expression line
            lines = code.rstrip().split("\n")
            lines[-1] = f"print({expr_src})"
            code = "\n".join(lines)
    except SyntaxError:
        pass  # Let the subprocess report the syntax error naturally

    # Use a placeholder that won't conflict with user code
    _PLACEHOLDER = "___IMAGE_DIR___"
    setup_lines = [
        _CODE_PROLOGUE,
        f"os.makedirs('{_PLACEHOLDER}', exist_ok=True)",
        f"images_dir = os.path.abspath('{_PLACEHOLDER}') if '{_PLACEHOLDER}' else '.'",
        code,
    ]
    return "\n".join(setup_lines).replace(_PLACEHOLDER, image_dir)


@tool(args_schema=PythonCodeInput)
def execute_python(code: str, image_dir: str = "./images", timeout_seconds: int = 30) -> str:
    """Execute Python code to solve math problems and generate visualizations.

    Use this tool for:
    - Solving equations, derivatives, integrals (sympy)
    - Numerical and matrix computation (numpy)
    - Generating charts and graphs (matplotlib)
    - Any computation that requires actual execution

    Always print your results. For charts, save to 'images/' directory and
    print the file path so the user can see the chart.
    """
    script = _build_execution_script(code, image_dir)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(script)
        script_path = f.name

    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            cwd=str(Path.cwd()),
        )
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        output_parts = []
        if stdout:
            output_parts.append(stdout)
        if stderr:
            output_parts.append(f"[stderr]:\n{stderr}")
        if result.returncode != 0:
            output_parts.append(f"[exit code: {result.returncode}]")

        output = "\n".join(output_parts) if output_parts else "(no output)"
        return output
    except FileNotFoundError:
        return f"Error: Python executable not found at '{sys.executable}'. Check your environment."
    except subprocess.TimeoutExpired:
        return f"Execution timed out after {timeout_seconds} seconds. Simplify your code or break it into smaller steps."
    finally:
        try:
            os.unlink(script_path)
        except OSError:
            pass
