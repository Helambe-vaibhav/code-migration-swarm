"""
state.py
--------
Defines the TypedDict state schema and Pydantic models for LangGraph state machine.
"""

from typing import TypedDict, List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ASTFunctionInfo(BaseModel):
    name: str
    args: List[str]
    is_async: bool = False
    docstring: Optional[str] = None
    has_type_hints: bool = False
    calls: List[str] = Field(default_factory=list)


class ASTClassInfo(BaseModel):
    name: str
    bases: List[str]
    methods: List[str] = Field(default_factory=list)
    docstring: Optional[str] = None


class ASTAnalysisResult(BaseModel):
    file_path: str
    imports: List[str] = Field(default_factory=list)
    internal_dependencies: List[str] = Field(default_factory=list)
    classes: List[ASTClassInfo] = Field(default_factory=list)
    functions: List[ASTFunctionInfo] = Field(default_factory=list)
    deprecated_patterns: List[str] = Field(default_factory=list)
    cyclomatic_complexity: int = 1
    summary: str = ""


class SandboxExecutionResult(BaseModel):
    success: bool
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    tests_total: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    error_summary: Optional[str] = None


class MigrationState(TypedDict):
    """
    Core state dictionary passed across LangGraph nodes.
    """
    project_path: str
    target_stack: str
    dependency_graph: Dict[str, List[str]]
    files_to_migrate: List[str]
    current_file_idx: int
    current_file: str
    source_code: str
    ast_analysis: Optional[Dict[str, Any]]
    migration_plan: Optional[str]
    migrated_code: Optional[str]
    synthesized_tests: Optional[str]
    sandbox_results: Optional[Dict[str, Any]]
    retry_count: int
    max_retries: int
    self_healing_feedback: Optional[str]
    human_approval_required: bool
    human_approved: bool
    human_comments: Optional[str]
    completed_files: List[Dict[str, Any]]
    pr_summary: Optional[str]
    status: str
    logs: List[Dict[str, Any]]
