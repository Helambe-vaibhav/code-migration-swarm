"""
agents/test_synthesizer.py
--------------------------
Test Synthesizer Agent: analyzes both legacy source and modernized code to synthesize
a rigorous pytest test suite covering business contracts, async execution, boundary conditions, and error paths.
"""

from pathlib import Path
from ..llm_client import LLMClient, extract_code_block


class TestSynthesizerAgent:
    SYSTEM_PROMPT = """You are a Principal QA Automation Engineer and Test-Driven Development (TDD) architect.
Your mission is to write an exhaustive, robust pytest suite for a newly modernized Python module.

Mandatory Testing Standards:
1. Always output complete, self-contained Python code in a single ```python ... ``` block.
2. If testing async functions, use `@pytest.mark.asyncio` on `async def test_*()` coroutines.
3. Import the module under test using its bare module name (e.g., if module is `service.py`, do `from service import ...` or `import service`).
4. Cover:
   - Happy paths (valid inputs, expected outputs)
   - Edge cases (empty inputs, zero values, boundary inputs)
   - Failure & validation error paths (expected exceptions, invalid types)
5. Rely only on standard library, `pytest`, `pytest-asyncio`, `pydantic`, or mocks.
6. Do NOT leave tests unfinished or pass blindly without assertions."""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def synthesize_tests(self, file_path: str, legacy_code: str, modernized_code: str) -> str:
        stem = Path(file_path).stem
        user_prompt = f"""Module Under Test: {file_path} (importable as '{stem}')

Legacy Reference Code:
```python
{legacy_code}
```

Modernized Target Code:
```python
{modernized_code}
```

Generate a complete, production-grade pytest test suite testing '{stem}'."""

        raw_output = self.llm.invoke(self.SYSTEM_PROMPT, user_prompt, temperature=0.1)
        return extract_code_block(raw_output)
