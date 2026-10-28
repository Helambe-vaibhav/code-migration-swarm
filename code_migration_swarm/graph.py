"""
graph.py
--------
Assembles the cyclic multi-agent StateGraph in LangGraph.
Implements topological module sequencing, self-healing compiler/test loops,
and human-in-the-loop interruption checkpoints.
"""

from pathlib import Path
from typing import Dict, Any, Literal
from datetime import datetime

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from .state import MigrationState
from .ast_analyzer import CodeASTAnalyzer
from .llm_client import LLMClient, get_llm_client
from .sandbox import ExecutionSandbox
from .agents import (
    ArchitectAgent,
    TranspilerAgent,
    TestSynthesizerAgent,
    SelfHealerAgent,
    ReviewerAgent,
)


class SwarmGraphBuilder:
    """
    Constructs and compiles the LangGraph StateGraph for autonomous code migration.
    """

    def __init__(self, llm: LLMClient, timeout_seconds: int = 25):
        self.llm = llm
        self.sandbox = ExecutionSandbox(timeout_seconds=timeout_seconds)
        self.architect = ArchitectAgent(llm)
        self.transpiler = TranspilerAgent(llm)
        self.test_synthesizer = TestSynthesizerAgent(llm)
        self.self_healer = SelfHealerAgent(llm)
        self.reviewer = ReviewerAgent(llm)

    def _log(self, state: MigrationState, node: str, message: str, level: str = "INFO"):
        logs = state.get("logs", [])
        logs.append({
            "timestamp": datetime.now().isoformat(),
            "node": node,
            "message": message,
            "level": level
        })
        state["logs"] = logs

    # --- Node 1: AST Analyzer Node ---
    def ast_analyzer_node(self, state: MigrationState) -> Dict[str, Any]:
        project_path = state["project_path"]
        analyzer = CodeASTAnalyzer(project_path)

        dep_graph = analyzer.build_dependency_graph()
        order = analyzer.get_migration_order()

        if not order:
            # Fallback if no files found
            py_files = [str(p.relative_to(project_path)) for p in Path(project_path).rglob("*.py") if not p.name.startswith(".")]
            order = py_files or ["service.py"]

        current_file = order[0]
        full_path = Path(project_path) / current_file
        source_code = full_path.read_text(encoding="utf-8") if full_path.exists() else ""
        ast_result = analyzer.analyze_file(full_path) if full_path.exists() else None

        self._log(state, "ast_analyzer_node", f"Discovered {len(order)} modules. Topological order: {', '.join(order)}")

        return {
            "dependency_graph": dep_graph,
            "files_to_migrate": order,
            "current_file_idx": 0,
            "current_file": current_file,
            "source_code": source_code,
            "ast_analysis": ast_result.model_dump() if ast_result else {},
            "status": "ANALYZING",
            "retry_count": 0,
            "logs": state.get("logs", [])
        }

    # --- Node 2: Architect Node ---
    def architect_node(self, state: MigrationState) -> Dict[str, Any]:
        file_path = state["current_file"]
        source_code = state["source_code"]
        ast_info = state.get("ast_analysis") or {}
        target_stack = state.get("target_stack", "python_legacy_to_async_fastapi")

        self._log(state, "architect_node", f"Designing migration blueprint for '{file_path}'")
        plan = self.architect.plan_migration(file_path, source_code, ast_info, target_stack)

        return {
            "migration_plan": plan,
            "status": "ARCHITECTING",
            "logs": state.get("logs", [])
        }

    # --- Node 3: Transpiler Node ---
    def transpiler_node(self, state: MigrationState) -> Dict[str, Any]:
        file_path = state["current_file"]
        source_code = state["source_code"]
        plan = state.get("migration_plan") or ""
        ast_info = state.get("ast_analysis") or {}

        self._log(state, "transpiler_node", f"Transpiling '{file_path}' to modern async/typed code")
        migrated = self.transpiler.transpile(file_path, source_code, plan, ast_info)

        return {
            "migrated_code": migrated,
            "status": "TRANSPILING",
            "logs": state.get("logs", [])
        }

    # --- Node 4: Test Synthesizer Node ---
    def test_synthesizer_node(self, state: MigrationState) -> Dict[str, Any]:
        file_path = state["current_file"]
        legacy_code = state["source_code"]
        modern_code = state.get("migrated_code") or ""

        self._log(state, "test_synthesizer_node", f"Synthesizing pytest test suite for '{file_path}'")
        tests = self.test_synthesizer.synthesize_tests(file_path, legacy_code, modern_code)

        return {
            "synthesized_tests": tests,
            "status": "SYNTHESIZING_TESTS",
            "logs": state.get("logs", [])
        }

    # --- Node 5: Sandbox Execution Node ---
    def sandbox_execution_node(self, state: MigrationState) -> Dict[str, Any]:
        file_path = state["current_file"]
        migrated_code = state.get("migrated_code") or ""
        test_code = state.get("synthesized_tests") or ""

        # Collect previously completed dependency modules
        dep_files = {}
        for comp in state.get("completed_files", []):
            dep_files[comp["file_path"]] = comp["migrated_code"]

        self._log(state, "sandbox_execution_node", f"Executing pytest suite in sandbox for '{file_path}'")
        res = self.sandbox.evaluate_code_and_tests(
            migrated_code=migrated_code,
            module_name=file_path,
            test_code=test_code,
            dependency_files=dep_files
        )

        outcome_msg = f"Sandbox result: {'PASSED' if res.success else 'FAILED'} (Passed: {res.tests_passed}, Failed: {res.tests_failed})"
        self._log(state, "sandbox_execution_node", outcome_msg, level="INFO" if res.success else "WARNING")

        return {
            "sandbox_results": res.model_dump(),
            "status": "SANDBOX_EVALUATED",
            "logs": state.get("logs", [])
        }

    # --- Node 6: Self-Healer Node (Cycle) ---
    def self_healer_node(self, state: MigrationState) -> Dict[str, Any]:
        file_path = state["current_file"]
        current_code = state.get("migrated_code") or ""
        test_code = state.get("synthesized_tests") or ""
        sandbox_res = state.get("sandbox_results") or {}
        error_summary = sandbox_res.get("error_summary") or sandbox_res.get("stderr") or "Unknown error"
        retries = state.get("retry_count", 0) + 1

        self._log(state, "self_healer_node", f"Self-healing '{file_path}' (Attempt {retries}/{state.get('max_retries', 3)})", level="WARNING")
        repaired_code = self.self_healer.repair(file_path, current_code, test_code, error_summary, retries)

        return {
            "migrated_code": repaired_code,
            "retry_count": retries,
            "self_healing_feedback": error_summary,
            "status": "SELF_HEALING",
            "logs": state.get("logs", [])
        }

    # --- Node 7: Human Review Node (HITL) ---
    def human_review_node(self, state: MigrationState) -> Dict[str, Any]:
        file_path = state["current_file"]
        self._log(state, "human_review_node", f"Human review requested for '{file_path}' after exceeding retry limit", level="CAUTION")
        return {
            "human_approval_required": True,
            "status": "WAITING_APPROVAL",
            "logs": state.get("logs", [])
        }

    # --- Node 8: Module Completed Node ---
    def module_completed_node(self, state: MigrationState) -> Dict[str, Any]:
        current_idx = state.get("current_file_idx", 0)
        files = state.get("files_to_migrate", [])
        file_path = state["current_file"]
        legacy_code = state["source_code"]
        modern_code = state.get("migrated_code") or ""
        tests = state.get("synthesized_tests") or ""
        sandbox_res = state.get("sandbox_results") or {}

        diff = self.reviewer.compute_diff(file_path, legacy_code, modern_code)

        completed = list(state.get("completed_files", []))
        completed.append({
            "file_path": file_path,
            "legacy_code": legacy_code,
            "migrated_code": modern_code,
            "synthesized_tests": tests,
            "diff": diff,
            "retries": state.get("retry_count", 0),
            "tests_passed": sandbox_res.get("tests_passed", 0)
        })

        next_idx = current_idx + 1
        self._log(state, "module_completed_node", f"Module '{file_path}' migrated successfully! ({next_idx}/{len(files)})")

        updates: Dict[str, Any] = {
            "completed_files": completed,
            "current_file_idx": next_idx,
            "retry_count": 0,
            "human_approval_required": False,
            "status": "MODULE_COMPLETED",
            "logs": state.get("logs", [])
        }

        # If more files remain, prepare next file
        if next_idx < len(files):
            next_file = files[next_idx]
            project_path = state["project_path"]
            full_path = Path(project_path) / next_file
            analyzer = CodeASTAnalyzer(project_path)

            updates["current_file"] = next_file
            updates["source_code"] = full_path.read_text(encoding="utf-8") if full_path.exists() else ""
            updates["ast_analysis"] = analyzer.analyze_file(full_path).model_dump() if full_path.exists() else {}
            updates["migrated_code"] = None
            updates["synthesized_tests"] = None
            updates["migration_plan"] = None
            updates["sandbox_results"] = None

        return updates

    # --- Node 9: PR Generator Node ---
    def pr_generator_node(self, state: MigrationState) -> Dict[str, Any]:
        completed = state.get("completed_files", [])
        project_path = state.get("project_path", "")

        self._log(state, "pr_generator_node", f"Generating Pull Request summary for {len(completed)} migrated files")
        pr_text = self.reviewer.generate_pr_summary(project_path, completed)

        return {
            "pr_summary": pr_text,
            "status": "COMPLETED",
            "logs": state.get("logs", [])
        }

    # --- Conditional Edge Routers ---
    def route_after_sandbox(self, state: MigrationState) -> Literal["module_completed_node", "self_healer_node", "human_review_node"]:
        sandbox_res = state.get("sandbox_results") or {}
        if sandbox_res.get("success", False):
            return "module_completed_node"

        retries = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 3)

        if retries < max_retries:
            return "self_healer_node"
        else:
            return "human_review_node"

    def route_after_module_completed(self, state: MigrationState) -> Literal["architect_node", "pr_generator_node"]:
        idx = state.get("current_file_idx", 0)
        total = len(state.get("files_to_migrate", []))
        if idx < total:
            return "architect_node"
        return "pr_generator_node"

    def route_after_human_review(self, state: MigrationState) -> Literal["module_completed_node", "pr_generator_node"]:
        if state.get("human_approved", False):
            return "module_completed_node"
        return "pr_generator_node"

    # --- Graph Assembly ---
    def build(self, with_checkpointer: bool = True):
        workflow = StateGraph(MigrationState)

        # Add Nodes
        workflow.add_node("ast_analyzer_node", self.ast_analyzer_node)
        workflow.add_node("architect_node", self.architect_node)
        workflow.add_node("transpiler_node", self.transpiler_node)
        workflow.add_node("test_synthesizer_node", self.test_synthesizer_node)
        workflow.add_node("sandbox_execution_node", self.sandbox_execution_node)
        workflow.add_node("self_healer_node", self.self_healer_node)
        workflow.add_node("human_review_node", self.human_review_node)
        workflow.add_node("module_completed_node", self.module_completed_node)
        workflow.add_node("pr_generator_node", self.pr_generator_node)

        # Standard Sequential Edges
        workflow.add_edge(START, "ast_analyzer_node")
        workflow.add_edge("ast_analyzer_node", "architect_node")
        workflow.add_edge("architect_node", "transpiler_node")
        workflow.add_edge("transpiler_node", "test_synthesizer_node")
        workflow.add_edge("test_synthesizer_node", "sandbox_execution_node")

        # Cyclic Self-Healing Loop Edge
        workflow.add_edge("self_healer_node", "sandbox_execution_node")

        # Conditional Branching after Sandbox
        workflow.add_conditional_edges(
            "sandbox_execution_node",
            self.route_after_sandbox,
            {
                "module_completed_node": "module_completed_node",
                "self_healer_node": "self_healer_node",
                "human_review_node": "human_review_node"
            }
        )

        # Conditional Branching after Module Completed (Next module vs Finish)
        workflow.add_conditional_edges(
            "module_completed_node",
            self.route_after_module_completed,
            {
                "architect_node": "architect_node",
                "pr_generator_node": "pr_generator_node"
            }
        )

        # Conditional Branching after Human Review
        workflow.add_conditional_edges(
            "human_review_node",
            self.route_after_human_review,
            {
                "module_completed_node": "module_completed_node",
                "pr_generator_node": "pr_generator_node"
            }
        )

        workflow.add_edge("pr_generator_node", END)

        checkpointer = MemorySaver() if with_checkpointer else None
        interrupts = ["human_review_node"] if with_checkpointer else []
        return workflow.compile(
            checkpointer=checkpointer,
            interrupt_before=interrupts
        )
