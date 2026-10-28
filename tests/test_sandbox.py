"""
tests/test_sandbox.py
---------------------
Tests verifying execution sandbox evaluation, syntax error capture, and pytest output parsing.
"""

from code_migration_swarm.sandbox import ExecutionSandbox


def test_sandbox_passing_test():
    sandbox = ExecutionSandbox(timeout_seconds=10)
    migrated_code = """
def add(a: int, b: int) -> int:
    return a + b
"""
    test_code = """
from target_mod import add

def test_add_success():
    assert add(2, 3) == 5
"""
    result = sandbox.evaluate_code_and_tests(
        migrated_code=migrated_code,
        module_name="target_mod.py",
        test_code=test_code
    )

    assert result.success is True
    assert result.exit_code == 0
    assert result.tests_passed == 1


def test_sandbox_syntax_error():
    sandbox = ExecutionSandbox(timeout_seconds=10)
    invalid_code = "def broken_syntax( {:"
    test_code = "def test_noop(): pass"

    result = sandbox.evaluate_code_and_tests(
        migrated_code=invalid_code,
        module_name="invalid.py",
        test_code=test_code
    )

    assert result.success is False
    assert result.error_summary is not None
    assert "Syntax Error" in result.error_summary


def test_sandbox_failing_assertion():
    sandbox = ExecutionSandbox(timeout_seconds=10)
    code = "def compute(): return 42"
    failing_test = """
from testee import compute
def test_fails():
    assert compute() == 999
"""
    result = sandbox.evaluate_code_and_tests(
        migrated_code=code,
        module_name="testee.py",
        test_code=failing_test
    )

    assert result.success is False
    assert result.exit_code != 0
    assert result.tests_failed == 1
