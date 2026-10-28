"""
server.py
---------
FastAPI web server providing REST endpoints and serving the modern interactive
dashboard for visual monitoring, DAG node tracking, code diffs, and HITL approvals.
"""

import os
import sys
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from code_migration_swarm.llm_client import get_llm_client
from code_migration_swarm.graph import SwarmGraphBuilder
from code_migration_swarm.state import MigrationState

app = FastAPI(title="RefactorSwarm Web Dashboard", version="1.0.0")

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# In-memory session manager
swarm_session = {
    "is_running": False,
    "graph": None,
    "thread_config": {"configurable": {"thread_id": "web_dashboard_session_001"}},
    "state": None,
    "completed_files": [],
    "logs": [],
    "status": "IDLE",
    "pr_summary": None,
    "active_node": "NONE",
    "human_review_required": False
}


class StartMigrationRequest(BaseModel):
    target_dir: str = "benchmarks/legacy_payment_service"
    provider: str = "ollama"
    model: str = "qwen2.5-coder:14b"
    max_retries: int = 3
    target_stack: str = "python_legacy_to_async_fastapi"


class HumanApprovalRequest(BaseModel):
    approved: bool
    comments: Optional[str] = None


def run_swarm_worker(req: StartMigrationRequest):
    global swarm_session
    swarm_session["is_running"] = True
    swarm_session["status"] = "RUNNING"
    swarm_session["logs"] = []
    swarm_session["completed_files"] = []
    swarm_session["pr_summary"] = None
    swarm_session["human_review_required"] = False

    target_path = Path(req.target_dir).resolve()
    if not target_path.exists():
        target_path = Path(__file__).parent / req.target_dir

    llm = get_llm_client(provider=req.provider, model=req.model)
    builder = SwarmGraphBuilder(llm=llm)
    graph = builder.build(with_checkpointer=True)
    swarm_session["graph"] = graph

    initial_state: MigrationState = {
        "project_path": str(target_path),
        "target_stack": req.target_stack,
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
        "max_retries": req.max_retries,
        "self_healing_feedback": None,
        "human_approval_required": False,
        "human_approved": False,
        "human_comments": None,
        "completed_files": [],
        "pr_summary": None,
        "status": "INITIALIZED",
        "logs": []
    }

    swarm_session["state"] = initial_state
    config = swarm_session["thread_config"]

    try:
        for event in graph.stream(initial_state, config=config):
            for node_name, node_output in event.items():
                swarm_session["active_node"] = node_name
                swarm_session["status"] = node_output.get("status", "PROCESSING")
                if "logs" in node_output:
                    swarm_session["logs"] = node_output["logs"]
                if "completed_files" in node_output:
                    swarm_session["completed_files"] = node_output["completed_files"]
                if "pr_summary" in node_output:
                    swarm_session["pr_summary"] = node_output["pr_summary"]
                if node_name == "human_review_node":
                    swarm_session["human_review_required"] = True
                    swarm_session["status"] = "WAITING_APPROVAL"
                    return

        swarm_session["status"] = "COMPLETED"
        swarm_session["is_running"] = False
    except Exception as ex:
        swarm_session["status"] = "ERROR"
        swarm_session["is_running"] = False
        swarm_session["logs"].append({
            "timestamp": "now",
            "node": "system",
            "message": f"Execution error: {str(ex)}",
            "level": "ERROR"
        })


@app.get("/")
def get_index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/status")
def get_status():
    return {
        "is_running": swarm_session["is_running"],
        "status": swarm_session["status"],
        "active_node": swarm_session["active_node"],
        "human_review_required": swarm_session["human_review_required"],
        "completed_count": len(swarm_session["completed_files"]),
        "completed_files": [
            {
                "file_path": cf["file_path"],
                "retries": cf.get("retries", 0),
                "tests_passed": cf.get("tests_passed", 0)
            } for cf in swarm_session["completed_files"]
        ],
        "pr_summary": swarm_session["pr_summary"],
        "logs": swarm_session["logs"][-30:]
    }


@app.get("/api/diff/{file_name}")
def get_file_diff(file_name: str):
    for cf in swarm_session["completed_files"]:
        if cf["file_path"] == file_name or Path(cf["file_path"]).name == file_name:
            return {
                "file_path": cf["file_path"],
                "diff": cf.get("diff", ""),
                "legacy_code": cf.get("legacy_code", ""),
                "migrated_code": cf.get("migrated_code", ""),
                "tests": cf.get("synthesized_tests", "")
            }
    raise HTTPException(status_code=404, detail="File diff not found")


@app.post("/api/start")
def start_migration(req: StartMigrationRequest, bg_tasks: BackgroundTasks):
    if swarm_session["is_running"]:
        return JSONResponse({"status": "already_running", "message": "Migration is already running."}, status_code=400)
    bg_tasks.add_task(run_swarm_worker, req)
    return {"status": "started", "message": "Autonomous migration swarm launched."}


@app.post("/api/approve")
def submit_approval(req: HumanApprovalRequest, bg_tasks: BackgroundTasks):
    if not swarm_session["human_review_required"]:
        return JSONResponse({"status": "no_review_needed", "message": "No human review is currently pending."}, status_code=400)

    graph = swarm_session["graph"]
    config = swarm_session["thread_config"]
    graph.update_state(config, {"human_approved": req.approved, "human_approval_required": False})
    swarm_session["human_review_required"] = False
    swarm_session["status"] = "RESUMING"

    # Resume graph execution in background
    def resume_worker():
        for event in graph.stream(None, config=config):
            for node_name, node_output in event.items():
                swarm_session["active_node"] = node_name
                swarm_session["status"] = node_output.get("status", "PROCESSING")
                if "logs" in node_output:
                    swarm_session["logs"] = node_output["logs"]
                if "completed_files" in node_output:
                    swarm_session["completed_files"] = node_output["completed_files"]
                if "pr_summary" in node_output:
                    swarm_session["pr_summary"] = node_output["pr_summary"]
        swarm_session["status"] = "COMPLETED"
        swarm_session["is_running"] = False

    bg_tasks.add_task(resume_worker)
    return {"status": "resumed", "message": f"Review submitted. Approved: {req.approved}"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
