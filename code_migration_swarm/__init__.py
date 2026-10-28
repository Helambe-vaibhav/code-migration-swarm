"""
code_migration_swarm package
----------------------------
Autonomous Enterprise Code Migration & Test-Driven Refactoring Swarm.
"""

from .state import MigrationState, ASTAnalysisResult, SandboxExecutionResult
from .ast_analyzer import CodeASTAnalyzer
from .llm_client import get_llm_client, LLMClient
from .sandbox import ExecutionSandbox
from .graph import SwarmGraphBuilder

__version__ = "1.0.0"

__all__ = [
    "MigrationState",
    "ASTAnalysisResult",
    "SandboxExecutionResult",
    "CodeASTAnalyzer",
    "get_llm_client",
    "LLMClient",
    "ExecutionSandbox",
    "SwarmGraphBuilder",
]
