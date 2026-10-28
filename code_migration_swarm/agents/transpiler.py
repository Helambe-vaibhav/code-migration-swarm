"""
agents/transpiler.py
--------------------
Transpiler Agent: transforms legacy synchronous, untyped code into modern,
fully typed, asynchronous Python 3.12+ code adhering to the architecture blueprint.
"""

from typing import Dict, Any
from ..llm_client import LLMClient, extract_code_block


class TranspilerAgent:
    SYSTEM_PROMPT = """You are an elite Senior Staff Python Engineer specializing in automated code transpilation and refactoring.
Your job is to rewrite legacy Python code into clean, modern, production-grade Python 3.12+ code.

Mandatory Guidelines:
1. Always output complete, self-contained Python code in a single ```python ... ``` block.
2. Fully type-annotate every function argument and return type using typing and Pydantic v2 schemas.
3. Replace synchronous blocking operations (time.sleep, requests.get) with native async equivalents (asyncio.sleep, httpx.AsyncClient).
4. Do NOT leave TODOs or placeholders; implement complete working logic.
5. Preserve public method/function signatures and business logic invariants.
6. Return ONLY the code block and brief docstring comments inside the code."""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def transpile(self, file_path: str, source_code: str, migration_plan: str, ast_analysis: Dict[str, Any]) -> str:
        user_prompt = f"""Target File: {file_path}

Architectural Migration Blueprint:
{migration_plan}

Legacy Source Code:
```python
{source_code}
```

Generate the fully modernized, typed, and asynchronous replacement Python code."""

        raw_output = self.llm.invoke(self.SYSTEM_PROMPT, user_prompt, temperature=0.1)
        return extract_code_block(raw_output)
