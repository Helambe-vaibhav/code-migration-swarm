#!/usr/bin/env python3
"""
cli.py
------
Rich-powered command-line interface for the Autonomous Code Migration Swarm.
"""

import os
import sys
import argparse
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm

from code_migration_swarm.llm_client import get_llm_client
from code_migration_swarm.graph import SwarmGraphBuilder
from code_migration_swarm.state import MigrationState


console = Console()


def print_banner():
    banner = """
[bold cyan]  ██████╗ ███████╗███████╗ █████╗  ██████╗████████╗ ██████╗ ██████╗ 
  ██╔══██╗██╔════╝██╔════╝██╔══██╗██╔════╝╚══██╔══╝██╔═══██╗██╔══██╗
  ██████╔╝█████╗  █████╗  ███████║██║        ██║   ██║   ██║██████╔╝
  ██╔══██╗██╔══╝  ██╔══╝  ██╔══██║██║        ██║   ██║   ██║██╔══██╗
  ██║  ██║███████╗██║     ██║  ██║╚██████╗   ██║   ╚██████╔╝██║  ██║
  ╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝  ╚═╝ ╚═════╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝[/bold cyan]
[dim]  Autonomous Enterprise Code Migration & Test-Driven Refactoring Swarm (LangGraph)[/dim]
    """
    console.print(banner)


def run_cli():
    parser = argparse.ArgumentParser(description="Autonomous Enterprise Code Migration Swarm")
    parser.add_argument("--target", "-t", type=str, default="benchmarks/legacy_payment_service", help="Target project directory to migrate")
    parser.add_argument("--provider", "-p", type=str, default="ollama", choices=["ollama", "openai", "mock"], help="LLM Provider")
    parser.add_argument("--model", "-m", type=str, default="qwen2.5-coder:14b", help="Model name")
    parser.add_argument("--retries", "-r", type=int, default=3, help="Max self-healing retries before human-in-the-loop")
    parser.add_argument("--stack", "-s", type=str, default="python_legacy_to_async_fastapi", help="Target architecture stack")
    args = parser.parse_args()

    print_banner()

    target_dir = Path(args.target).resolve()
    if not target_dir.exists():
        console.print(f"[bold red]Error:[/bold red] Target directory '{target_dir}' does not exist.")
        sys.exit(1)

    console.print(Panel(
        f"[bold green]Target Project:[/bold green] {target_dir}\n"
        f"[bold green]LLM Provider:[/bold green] {args.provider.upper()} ({args.model})\n"
        f"[bold green]Architecture:[/bold green] {args.stack}\n"
        f"[bold green]Max Retries:[/bold green] {args.retries}",
        title="[bold yellow]Swarm Configuration[/bold yellow]",
        border_style="cyan"
    ))

    # Initialize LLM & Graph
    with console.status("[bold green]Initializing Multi-Agent LangGraph Swarm...[/bold green]", spinner="dots"):
        llm = get_llm_client(provider=args.provider, model=args.model)
        builder = SwarmGraphBuilder(llm=llm)
        graph = builder.build(with_checkpointer=True)

    initial_state: MigrationState = {
        "project_path": str(target_dir),
        "target_stack": args.stack,
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
        "max_retries": args.retries,
        "self_healing_feedback": None,
        "human_approval_required": False,
        "human_approved": False,
        "human_comments": None,
        "completed_files": [],
        "pr_summary": None,
        "status": "INITIALIZED",
        "logs": []
    }

    config = {"configurable": {"thread_id": "cli_migration_session_001"}}
    console.print("\n[bold cyan]🚀 Starting Autonomous Migration Swarm Loop...[/bold cyan]\n")

    current_state = initial_state
    for event in graph.stream(current_state, config=config):
        for node_name, node_output in event.items():
            status = node_output.get("status", "")
            console.print(f"[bold blue]► Agent Node:[/bold blue] [magenta]{node_name}[/magenta] | Status: [yellow]{status}[/yellow]")

            # Print AST breakdown
            if node_name == "ast_analyzer_node":
                files = node_output.get("files_to_migrate", [])
                dep_table = Table(title="AST Topological Migration Sequence", border_style="dim")
                dep_table.add_column("Order", style="cyan", justify="right")
                dep_table.add_column("Module File", style="green")
                for i, f in enumerate(files, 1):
                    dep_table.add_row(str(i), f)
                console.print(dep_table)

            # Print Sandbox Outcome
            elif node_name == "sandbox_execution_node":
                sb = node_output.get("sandbox_results", {})
                if sb.get("success"):
                    console.print(f"  [bold green]✔ Pytest Execution PASSED![/bold green] ({sb.get('tests_passed', 0)} passed)")
                else:
                    console.print(f"  [bold red]✖ Pytest Execution FAILED![/bold red] ({sb.get('tests_failed', 0)} failed)")
                    if sb.get("error_summary"):
                        console.print(Panel(sb['error_summary'], title="Diagnostic Error Summary", border_style="red"))

            # Print Self-Healer Loop
            elif node_name == "self_healer_node":
                retries = node_output.get("retry_count", 0)
                console.print(f"  [bold yellow]⚡ Closed-Loop Self-Healing Activated (Retry {retries}/{args.retries})[/bold yellow]")

            # Print Completed Module Diff
            elif node_name == "module_completed_node":
                completed = node_output.get("completed_files", [])
                if completed:
                    last_comp = completed[-1]
                    console.print(f"\n[bold green]✨ Module Modernization Complete:[/bold green] [bold]{last_comp['file_path']}[/bold]")
                    if last_comp.get("diff"):
                        console.print(Syntax(last_comp["diff"][:1200], "diff", theme="monokai", line_numbers=True))

            # Human-in-the-Loop Interruption
            elif node_name == "human_review_node":
                console.print("\n[bold red]🚨 Human Review Interruption Triggered![/bold red]")
                approved = Confirm.ask("Do you approve proceeding with this module migration?")
                graph.update_state(config, {"human_approved": approved, "human_approval_required": False})

            # Pull Request Generation
            elif node_name == "pr_generator_node":
                pr_md = node_output.get("pr_summary", "")
                console.print("\n" + "=" * 80)
                console.print(Panel(pr_md, title="[bold green]Executive Pull Request & Migration Changelog[/bold green]", border_style="green"))

    console.print("\n[bold green]🎉 Migration Swarm Execution Completed Successfully![/bold green]\n")


if __name__ == "__main__":
    run_cli()
