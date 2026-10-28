"""
agents/self_healer.py
---------------------
Self-Healer Agent: analyzes compiler diagnostics, pytest tracebacks, and assertion failures
to autonomously repair modernized code within the closed-loop LangGraph cycle.
"""

from pathlib import Path
from ..llm_client import LLMClient, extract_code_block


class SelfHealerAgent:
    SYSTEM_PROMPT = """You are a World-Class Diagnostic & Autonomous Debugging Engineer.
Your mission is to analyze why a modernized Python module failed its compilation or pytest test suite, and generate a surgical, fully corrected version of the code.

Diagnostic Guidelines:
1. Thoroughly read the compiler error or pytest traceback and identify the root cause (e.g. unhandled await, missing import, type mismatch, wrong parameter name).
2. Fix the error directly in the code without breaking the contract or removing existing features.
3. Output ONLY the complete corrected Python code inside a ```python ... ``` block.
4. Do not output incomplete snippets."""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def repair(self, file_path: str, current_code: str, test_code: str, error_summary: str, retry_count: int) -> str:
        user_prompt = f"""Target File: {file_path}
Retry Attempt: {retry_count}

Failure Diagnostic / Traceback:
```
{error_summary}
```

Current Module Code:
```python
{current_code}
```

Active Test Suite:
```python
{test_code}
```

Please diagnose the issue and return the complete, corrected Python module code."""

        raw_output = self.llm.invoke(self.SYSTEM_PROMPT, user_prompt, temperature=0.1)
        return extract_code_block(raw_output)
