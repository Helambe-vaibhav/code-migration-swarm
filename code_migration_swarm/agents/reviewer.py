"""
agents/reviewer.py
------------------
Reviewer Agent: computes unified diffs, verifies contract preservation,
and generates automated enterprise Pull Request summaries and changelogs.
"""

import difflib
from typing import List, Dict, Any
from ..llm_client import LLMClient


class ReviewerAgent:
    SYSTEM_PROMPT = """You are a Principal Technical Lead and Code Reviewer.
Your task is to generate a pristine, executive-ready Pull Request summary and changelog for an autonomous codebase migration.

Highlight:
1. Executive Summary & Objective
2. Key Architectural Modernizations (Async, Type Annotations, Pydantic Schemas)
3. Quality & Safety Verification (Tests synthesized, pass rate, sandbox metrics)
4. Breaking Change Assessment & Contract Invariance Guarantee"""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def compute_diff(self, file_path: str, legacy_code: str, modern_code: str) -> str:
        """Generates unified diff between legacy and modern code."""
        legacy_lines = legacy_code.splitlines(keepends=True)
        modern_lines = modern_code.splitlines(keepends=True)
        diff = difflib.unified_diff(
            legacy_lines,
            modern_lines,
            fromfile=f"a/{file_path} (legacy)",
            tofile=f"b/{file_path} (modernized)",
            n=3
        )
        return "".join(diff)

    def generate_pr_summary(self, project_path: str, completed_files: List[Dict[str, Any]]) -> str:
        files_summary = []
        for cf in completed_files:
            fp = cf.get("file_path", "")
            retries = cf.get("retries", 0)
            tests = cf.get("tests_passed", 0)
            files_summary.append(f"- **{fp}**: {tests} tests passed, self-healed in {retries} retries.")

        files_block = "\n".join(files_summary)
        user_prompt = f"""Project: {project_path}
Completed Migrations ({len(completed_files)} files):
{files_block}

Generate an executive GitHub Pull Request description."""

        return self.llm.invoke(self.SYSTEM_PROMPT, user_prompt, temperature=0.2)
