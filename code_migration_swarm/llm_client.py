"""
llm_client.py
-------------
Unified LLM client interface supporting:
1. Local Ollama (qwen2.5-coder:14b, deepseek-r1, qwen3)
2. OpenAI API
3. Deterministic Mock Provider (for offline testing & CI/CD)
"""

import os
import json
import re
from typing import Optional, Dict, Any, List
import httpx


class LLMClient:
    """Base interface for all LLM providers in the swarm."""

    def invoke(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        raise NotImplementedError


class OllamaClient(LLMClient):
    """Interacts with local Ollama service (default: qwen2.5-coder:14b)."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen2.5-coder:14b", timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def invoke(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "options": {
                "temperature": temperature
            },
            "stream": False
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "")


class OpenAIClient(LLMClient):
    """Interacts with OpenAI API using standard HTTP or langchain_openai."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model

    def invoke(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not configured.")
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature
        }
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]


class MockClient(LLMClient):
    """
    Deterministic rule-driven mock provider for offline demonstrations,
    regression tests, and CI/CD validation without requiring an active LLM.
    """

    def invoke(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        sys_lower = system_prompt.lower()
        user_lower = user_prompt.lower()

        # 1. Test Synthesizer
        if "qa automation" in sys_lower or "test-driven development" in sys_lower or "synthesize a" in user_lower:
            match = re.search(r"importable as '([^']+)'", user_prompt)
            mod_stem = match.group(1) if match else "target_module"
            return (
                f"```python\n"
                f"import pytest\n"
                f"import asyncio\n"
                f"from {mod_stem} import ModernRecord, process_record\n\n"
                f"@pytest.mark.asyncio\n"
                f"async def test_{mod_stem}_record_success():\n"
                f"    res = await process_record('rec_001', {{'amount': 100}})\n"
                f"    assert res.id == 'rec_001'\n"
                f"    assert res.status == 'PROCESSED'\n"
                f"    assert res.metadata['amount'] == 100\n"
                f"```"
            )

        # 2. Self Healer
        if "diagnostic & autonomous" in sys_lower or "traceback" in user_lower or "self-healer" in user_lower:
            return (
                "```python\n"
                "from typing import Optional, Dict, Any\n"
                "from pydantic import BaseModel\n"
                "import asyncio\n\n"
                "class ModernRecord(BaseModel):\n"
                "    id: str\n"
                "    status: str = 'ACTIVE'\n"
                "    metadata: Dict[str, Any] = {}\n\n"
                "async def process_record(record_id: str, payload: Dict[str, Any]) -> ModernRecord:\n"
                "    await asyncio.sleep(0.01)\n"
                "    return ModernRecord(id=record_id, status='PROCESSED', metadata=payload)\n"
                "```"
            )

        # 3. Transpiler
        if "code transpilation" in sys_lower or "transpile" in user_lower or "modernized, typed" in user_lower:
            return (
                "```python\n"
                "\"\"\"\n"
                "Modernized asynchronous module.\n"
                "Refactored with strict typing, Pydantic schemas, and non-blocking I/O.\n"
                "\"\"\"\n"
                "from typing import Optional, Dict, Any, List\n"
                "from pydantic import BaseModel, Field\n"
                "import asyncio\n\n"
                "class ModernRecord(BaseModel):\n"
                "    id: str\n"
                "    status: str = 'ACTIVE'\n"
                "    metadata: Dict[str, Any] = Field(default_factory=dict)\n\n"
                "async def process_record(record_id: str, payload: Dict[str, Any]) -> ModernRecord:\n"
                "    await asyncio.sleep(0.01)\n"
                "    return ModernRecord(id=record_id, status='PROCESSED', metadata=payload)\n"
                "```"
            )

        # 4. Architect
        if "principal software architect" in sys_lower or "architectural migration" in user_lower:
            return (
                "### Architectural Migration Strategy\n"
                "1. **Contract Invariant**: Maintain existing public interface and return payloads.\n"
                "2. **Async Modernization**: Convert blocking I/O into native `async/await` coroutines using `asyncio` and `httpx.AsyncClient`.\n"
                "3. **Type Safety**: Apply strict Pydantic v2 schemas and explicit Python 3.12 type annotations.\n"
                "4. **Error Handling**: Replace bare excepts with domain-specific exceptions.\n"
            )

        # 5. Reviewer
        if "code reviewer" in sys_lower or "pull request" in user_lower:
            return (
                "## 🚀 Automated Refactoring & Migration Summary\n\n"
                "### Key Changes:\n"
                "- Converted synchronous blocking calls to native async coroutines.\n"
                "- Integrated Pydantic v2 models for schema validation.\n"
                "- Synthesized 100% passing pytest suites with boundary assertions.\n"
                "- Verified zero cyclomatic regressions across all target modules.\n"
            )

        return "Processed successfully."


def get_llm_client(provider: str = "ollama", model: Optional[str] = None) -> LLMClient:
    """Factory to instantiate the appropriate LLM client."""
    provider_clean = provider.lower().strip()
    if provider_clean == "ollama":
        target_model = model or "qwen2.5-coder:14b"
        return OllamaClient(model=target_model)
    elif provider_clean == "openai":
        target_model = model or "gpt-4o-mini"
        return OpenAIClient(model=target_model)
    elif provider_clean == "mock":
        return MockClient()
    else:
        # Fallback to local Ollama if available, otherwise Mock
        try:
            with httpx.Client(timeout=2.0) as client:
                resp = client.get("http://localhost:11434/api/tags")
                if resp.status_code == 200:
                    return OllamaClient(model=model or "qwen2.5-coder:14b")
        except Exception:
            pass
        return MockClient()


def extract_code_block(text: str, default_lang: str = "python") -> str:
    """Extracts code block from LLM markdown response."""
    pattern = rf"```{default_lang}?\n(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Fallback if no fence
    lines = text.strip().splitlines()
    filtered = [l for l in lines if not l.startswith("```")]
    return "\n".join(filtered).strip()
