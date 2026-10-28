# RefactorSwarm: Autonomous Enterprise Code Migration & Test-Driven Refactoring Swarm

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.2+-purple.svg)](https://github.com/langchain-ai/langgraph)
[![LangChain](https://img.shields.io/badge/LangChain-1.4+-green.svg)](https://github.com/langchain-ai/langchain)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-teal.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An enterprise-grade, cyclic multi-agent system built with **LangGraph** and **LangChain** for autonomous code migration, AST-guided dependency sequencing, test-driven synthesis, and self-healing compiler/linter feedback loops.

---

## 🏛️ System Architecture

`RefactorSwarm` models codebase modernization as a stateful, cyclic directed graph using LangGraph's `StateGraph`:

```
                             [ START ]
                                 │
                                 ▼
                     ┌───────────────────────┐
                     │   AST Analyzer Node   │  ──> Builds Dependency DAG & Topological Order
                     └───────────┬───────────┘
                                 │
                                 ▼
                     ┌───────────────────────┐
                     │    Architect Node     │  ──> Analyzes Invariants & Designs Migration Plan
                     └───────────┬───────────┘
                                 │
                                 ▼
                     ┌───────────────────────┐
                     │    Transpiler Node    │  ──> Emits Async / Typed Modern Code (Pydantic v2)
                     └───────────┬───────────┘
                                 │
                                 ▼
                     ┌───────────────────────┐
                     │ Test Synthesizer Node │  ──> Synthesizes Strict Pytest TDD Suites
                     └───────────┬───────────┘
                                 │
                                 ▼
                     ┌───────────────────────┐
           ┌───────> │  Execution Sandbox    │  ──> Compiles & Runs Pytest Subprocess
           │         └───────────┬───────────┘
           │                     │
   (Tests Failed &               ├──[ Passed ]───────────────────────┐
    Retries < Max)               │                                   │
           │                     ▼                                   │
┌──────────┴────────┐   ┌─────────────────┐                          │
│ Self-Healer Node  │   │   Human Review  │ (Retries Exceeded        │
│ (Cyclic Repair)   │   │   Node (HITL)   │  or Breaking Contract)   │
└───────────────────┘   └────────┬────────┘                          │
                                 │                                   │
                                 ├──[ Approved ]─────────────────────┤
                                 │                                   │
                                 ▼                                   ▼
                     ┌───────────────────────┐           ┌───────────────────────┐
                     │     Module Finish     │ ──(More)─>│ Next Module in Topo   │
                     └───────────┬───────────┘           └───────────────────────┘
                                 │ (All Done)
                                 ▼
                     ┌───────────────────────┐
                     │   PR Generator Node   │  ──> Computes Diffs & Generates Executive PR
                     └───────────┬───────────┘
                                 │
                                 ▼
                              [ END ]
```

---

## ⚡ Key Engineering Features

1. **Topological AST Dependency Ordering:**
   - Employs native Python `ast` parsing to discover module hierarchies, internal imports, and legacy anti-patterns (`requests`, `time.sleep`, string-formatted SQL, bare excepts, missing types).
   - Resolves dependencies using `graphlib.TopologicalSorter` so leaf dependencies (models, utility schemas) are modernized and verified before dependent business services.

2. **Test-Driven Synthesis & Isolated Sandbox Execution:**
   - Synthesizes rigorous `pytest` suites using `@pytest.mark.asyncio`, covering valid paths, boundary edge cases, and schema validation.
   - Executes code in isolated temporary workspaces with dedicated `PYTHONPATH` sandboxes, capturing `exit_code`, stdout, stderr, and actionable tracebacks.

3. **Closed-Loop Self-Healing Feedback Cycle:**
   - If tests or compilation fails, LangGraph routes state to the `SelfHealerAgent`.
   - The healer diagnoses root causes (unhandled coroutines, missing imports, signature discrepancies) and iteratively repairs code within a bounded retry loop.

4. **Human-in-the-Loop (HITL) Checkpoints:**
   - Features configurable interruption thresholds (`interrupt_before=["human_review_node"]`) and state persistence with `MemorySaver`.
   - Engineers can inspect diffs and approve or abort before state changes are committed.

5. **Multi-Provider LLM Flexibility:**
   - **Local Ollama** (e.g. `qwen2.5-coder:14b`, `qwen3:14b`): 100% private, offline, zero cloud API fees.
   - **Cloud Providers**: OpenAI (`gpt-4o-mini`, `gpt-4o`), Anthropic, Google Gemini.
   - **Deterministic Mock Provider**: Lightning-fast offline verification and automated CI/CD runs.

---

## 📦 Project Structure

```
code-migration-swarm/
├── cli.py                             # Rich-powered interactive CLI
├── server.py                          # FastAPI web backend with REST endpoints
├── pyproject.toml                     # Package specification and scripts
├── requirements.txt                   # Production dependencies
├── code_migration_swarm/
│   ├── __init__.py
│   ├── state.py                       # TypedDict & Pydantic state schemas
│   ├── ast_analyzer.py                # AST static analysis & topological sorter
│   ├── llm_client.py                  # Multi-provider client (Ollama, OpenAI, Mock)
│   ├── sandbox.py                     # Subprocess compiler & pytest sandbox
│   ├── graph.py                       # LangGraph StateGraph orchestration
│   └── agents/
│       ├── __init__.py
│       ├── architect.py               # Blueprint & contract invariance planner
│       ├── transpiler.py              # Code modernizer & async/type converter
│       ├── test_synthesizer.py        # Pytest test suite generator
│       ├── self_healer.py             # Closed-loop diagnostic repair agent
│       └── reviewer.py                # Diff generator & PR description writer
├── benchmarks/
│   └── legacy_payment_service/        # Authentic legacy sample codebase
│       ├── models.py                  # Untyped Python 3.6 legacy classes
│       ├── database.py                # Synchronous blocking SQLite layer
│       └── service.py                 # Synchronous business logic
├── static/
│   ├── index.html                     # Modern glassmorphism dashboard UI
│   ├── style.css                      # Design system with glowing active nodes
│   └── app.js                         # Real-time state polling & diff viewer
└── tests/
    ├── test_ast_analyzer.py           # AST discovery and topological sorting tests
    ├── test_sandbox.py                # Execution sandbox unit tests
    └── test_swarm_graph.py            # End-to-end StateGraph integration tests
```

---

## 🚀 Quickstart Guide

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/Helambe-vaibhav/code-migration-swarm.git
cd code-migration-swarm

# Create virtual environment and install dependencies
uv venv .venv
source .venv/bin/activate
uv pip install -e .
```

### 2. Run Autonomous Migration via CLI

```bash
# Run with local Ollama (qwen2.5-coder:14b)
python cli.py --target benchmarks/legacy_payment_service --provider ollama

# Run with Deterministic Mock (Instant demo / CI/CD)
python cli.py --target benchmarks/legacy_payment_service --provider mock

# Run with OpenAI
export OPENAI_API_KEY="sk-..."
python cli.py --target benchmarks/legacy_payment_service --provider openai --model gpt-4o-mini
```

### 3. Launch Interactive Web Dashboard

```bash
# Start FastAPI server
python server.py
```
Open **`http://localhost:8000`** in your browser to monitor real-time agent execution, view glowing DAG state transitions, inspect live unified diffs, and authorize human-in-the-loop approvals.

---

## 🧪 Running Automated Tests

```bash
pytest -v tests/
```
All 7 unit and integration tests validate the AST parser, sandbox compiler, and full LangGraph state machine.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
