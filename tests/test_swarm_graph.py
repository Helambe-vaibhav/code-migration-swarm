"""
tests/test_swarm_graph.py
-------------------------
End-to-end integration test verifying LangGraph StateGraph execution,
node transitions, and state evolution using the deterministic MockClient.
"""

from pathlib import Path
from code_migration_swarm.llm_client import MockClient
from code_migration_swarm.graph import SwarmGraphBuilder
from code_migration_swarm.state import MigrationState


def test_swarm_graph_mock_run(tmp_path: Path):
    # Create simple target module to migrate
    sample_file = tmp_path / "simple_service.py"
    sample_file.write_text("""
def calculate(value):
    return value * 2
""")

    mock_llm = MockClient()
    builder = SwarmGraphBuilder(llm=mock_llm)
    graph = builder.build(with_checkpointer=False)

    initial_state: MigrationState = {
        "project_path": str(tmp_path),
        "target_stack": "python_legacy_to_async_fastapi",
        "dependency_graph": {},
        "files_to_migrate": [],
        "current_file_idx": 0,
        "current_file": "",
        "source_code": "",
        "ast_analysis": None,
        "migration_plan": None,
        "migrated_code": None,
        "synthesized_tests": None,
        "sandbox_results": None,
        "retry_count": 0,
        "max_retries": 3,
        "self_healing_feedback": None,
        "human_approval_required": False,
        "human_approved": False,
        "human_comments": None,
        "completed_files": [],
        "pr_summary": None,
        "status": "INITIALIZED",
        "logs": []
    }

    final_state = graph.invoke(initial_state)

    assert final_state["status"] == "COMPLETED"
    assert len(final_state["completed_files"]) >= 1
    assert final_state["pr_summary"] is not None
    assert "Automated Refactoring" in final_state["pr_summary"]
