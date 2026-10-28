"""
sandbox.py
----------
Isolated code execution sandbox.
Compiles migrated modules and executes synthesized pytest test suites,
capturing stdout, stderr, exit codes, and actionable stack traces for self-healing loops.
"""

import os
import sys
import tempfile
import subprocess
import py_compile
import re
from pathlib import Path
from typing import Dict, Any, Optional

from .state import SandboxExecutionResult


class ExecutionSandbox:
    """
    Manages safe runtime evaluation of modernized code and tests.
    """

    def __init__(self, timeout_seconds: int = 20):
        self.timeout_seconds = timeout_seconds

    def evaluate_code_and_tests(
        self,
        migrated_code: str,
        module_name: str,
        test_code: str,
        dependency_files: Optional[Dict[str, str]] = None
    ) -> SandboxExecutionResult:
        """
        Executes test suite against migrated code in an isolated directory.
        """
        with tempfile.TemporaryDirectory(prefix="swarm_sandbox_") as temp_dir:
            temp_path = Path(temp_dir)

            # Write dependency files if any
            if dependency_files:
                for dep_name, dep_content in dependency_files.items():
                    target_file = temp_path / dep_name
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    target_file.write_text(dep_content, encoding="utf-8")

            # Write target module
            module_file = temp_path / module_name
            module_file.parent.mkdir(parents=True, exist_ok=True)
            module_file.write_text(migrated_code, encoding="utf-8")

            # 1. Syntax Compilation Check
            try:
                py_compile.compile(str(module_file), doraise=True)
            except py_compile.PyCompileError as pe:
                return SandboxExecutionResult(
                    success=False,
                    exit_code=1,
                    stderr=str(pe),
                    error_summary=f"Syntax Error during compilation: {str(pe)}"
                )

            # Write test file
            test_file = temp_path / f"test_{Path(module_name).stem}.py"
            test_file.write_text(test_code, encoding="utf-8")

            # 2. Syntax Check Test File
            try:
                py_compile.compile(str(test_file), doraise=True)
            except py_compile.PyCompileError as pe:
                return SandboxExecutionResult(
                    success=False,
                    exit_code=1,
                    stderr=str(pe),
                    error_summary=f"Synthesized test compilation error: {str(pe)}"
                )

            # 3. Execute Pytest in isolated subprocess
            env = os.environ.copy()
            env["PYTHONPATH"] = str(temp_path) + os.pathsep + env.get("PYTHONPATH", "")

            # Use current virtualenv python if available
            python_bin = sys.executable

            cmd = [
                python_bin,
                "-m",
                "pytest",
                "-v",
                "--tb=short",
                "-o", "asyncio_mode=auto",
                str(test_file)
            ]

            try:
                proc = subprocess.run(
                    cmd,
                    cwd=str(temp_path),
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=self.timeout_seconds
                )

                stdout = proc.stdout
                stderr = proc.stderr
                exit_code = proc.returncode

                # Parse test metrics
                passed = 0
                failed = 0
                match_passed = re.search(r"(\d+)\s+passed", stdout)
                if match_passed:
                    passed = int(match_passed.group(1))

                match_failed = re.search(r"(\d+)\s+failed", stdout)
                if match_failed:
                    failed = int(match_failed.group(1))

                error_summary = None
                if exit_code != 0:
                    # Extract concise traceback summary
                    error_lines = []
                    for line in (stdout + "\n" + stderr).splitlines():
                        if any(marker in line for marker in ("ERROR", "FAIL", "AssertionError", "Traceback", "TypeError", "AttributeError")):
                            error_lines.append(line.strip())
                    error_summary = "\n".join(error_lines[-10:]) if error_lines else "Test suite failed with non-zero exit code."

                return SandboxExecutionResult(
                    success=(exit_code == 0),
                    exit_code=exit_code,
                    stdout=stdout,
                    stderr=stderr,
                    tests_total=passed + failed,
                    tests_passed=passed,
                    tests_failed=failed,
                    error_summary=error_summary
                )

            except subprocess.TimeoutExpired:
                return SandboxExecutionResult(
                    success=False,
                    exit_code=124,
                    error_summary=f"Sandbox execution timed out after {self.timeout_seconds} seconds (possible infinite loop or blocking call)."
                )
            except Exception as ex:
                return SandboxExecutionResult(
                    success=False,
                    exit_code=-1,
                    stderr=str(ex),
                    error_summary=f"Sandbox execution system error: {str(ex)}"
                )
