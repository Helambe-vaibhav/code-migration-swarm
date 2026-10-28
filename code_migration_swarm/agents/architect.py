"""
agents/architect.py
-------------------
Architect Agent: inspects legacy source AST, identifies architectural anti-patterns,
and formulates an invariant-preserving modernization strategy.
"""

from typing import Dict, Any
from ..llm_client import LLMClient


class ArchitectAgent:
    SYSTEM_PROMPT = """You are a Principal Software Architect specializing in legacy codebase modernization and high-throughput asynchronous Python architecture.
Your mission is to analyze legacy Python source code and AST findings, and design a precise migration blueprint to modern Python 3.12+ / FastAPI / async standards.

Strict Architectural Principles:
1. CONTRACT INVARIANCE: Public function names, class interfaces, and core business logic contracts MUST remain functionally compatible.
2. ASYNC MODERNIZATION: Transform blocking I/O (time.sleep, requests, sync database calls) to native non-blocking coroutines (asyncio, httpx).
3. TYPE SAFETY: Introduce explicit type hints and Pydantic v2 BaseModel schemas for data validation.
4. ERROR HANDLING: Replace bare excepts with domain-specific exceptions.
5. NO CODE BLOAT: Keep solutions concise, robust, and idiomatic.

Respond with a structured markdown migration blueprint."""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def plan_migration(self, file_path: str, source_code: str, ast_analysis: Dict[str, Any], target_stack: str) -> str:
        deprecated_summary = "\n- ".join(ast_analysis.get("deprecated_patterns", [])) or "None detected"
        classes_summary = ", ".join(c.get("name", "") for c in ast_analysis.get("classes", [])) or "None"
        funcs_summary = ", ".join(f.get("name", "") for f in ast_analysis.get("functions", [])) or "None"

        user_prompt = f"""Target File: {file_path}
Target Stack: {target_stack}

AST Analysis:
- Classes: {classes_summary}
- Functions: {funcs_summary}
- Complexity: {ast_analysis.get('cyclomatic_complexity', 1)}
- Deprecated / Anti-patterns:
- {deprecated_summary}

Source Code:
```python
{source_code}
```

Please outline the architectural migration blueprint for this module."""

        return self.llm.invoke(self.SYSTEM_PROMPT, user_prompt, temperature=0.1)
