# Agent Architecture

This document describes the organization of agents in this project.

## Directory Structure

```
agents/
├── chat_agent/          # Interactive conversational agent (MainAgent)
│   ├── agent.py         # ChatAgent implementation
│   ├── prompts.py       # Conversational prompts
│   └── exam_api_tool.py # Chat-specific tools
│
├── executor_agent/      # Autonomous background task executor
│   ├── executor.py      # ExecutorAgent implementation
│   └── prompts.py       # Task-specific instruction prompts
│
├── shared/              # Shared orchestrator utilities
│   └── workflow_tools.py # Workflow invocation tools (both agents use these)
│
└── task_agents/         # Specialized task subagents
    ├── scheduler/       # Calendar scheduling
    ├── suggestions/     # Proactive suggestions
    ├── assignment_assessment/  # Assignment analysis
    ├── exam_api/        # Exam management
    └── progress_tracking/      # Progress monitoring
```

## Agent Types

### 1. Orchestrator Agents

Located in `agents/chat_agent` and `agents/executor_agent`

- **ChatAgent** (`MainAgent`): Interactive conversational interface
  - User-facing chat loop
  - Can call workflow tools when needed
  - Conversational responses
  - Entry point: `main.py`

- **ExecutorAgent**: Autonomous task execution
  - Background/scheduled operations
  - No user interaction
  - Task-specific instruction prompts
  - Returns structured results (dict)
  - Entry point: Cron jobs, webhooks, or `test_executor.py`

### 2. Task Agents (Subagents)

Located in `agents/task_agents/*`

Each task agent:
- Has its own LangGraph workflow (`graph.py`)
- Has specialized tools (`tools.py`)
- Defines its own state (`state.py`)
- Can be invoked by orchestrators

Examples:
- **scheduler**: Calendar event management
- **suggestions**: Proactive study suggestions
- **assignment_assessment**: Assignment difficulty analysis

### 3. Shared Tools

Located in `agents/shared/workflow_tools.py`

Tools that both orchestrators can use:
- `run_scheduler_workflow(...)` - Schedule calendar events
- `assess_assignment(...)` - Analyze assignment difficulty
- `generate_suggestions(...)` - Generate proactive suggestions

These tools invoke the task agent workflows.

## Import Patterns

```python
# Orchestrators
from agents import MainAgent, ExecutorAgent
from agents.chat_agent import MainAgent

# Task agents (workflows)
from agents.task_agents.scheduler import scheduler_graph, SchedulerState
from agents.task_agents.suggestions import suggestions_graph

# Shared tools
from agents.shared.workflow_tools import run_scheduler_workflow
```

## Flow Examples

### ChatAgent Flow
```
User Input → ChatAgent → Decides to call run_scheduler_workflow()
                              ↓
                        scheduler_graph (task agent)
                              ↓
                        Returns structured result
                              ↓
                        ChatAgent formats for user
```

### ExecutorAgent Flow
```
Cron Trigger → ExecutorAgent.execute_schedule_meeting()
                    ↓
                Format task prompt
                    ↓
                Call scheduler_graph directly
                    ↓
                Return structured dict (logs, monitoring)
```

## Key Principles

1. **Orchestrators vs Task Agents**: Clear separation
   - Orchestrators: Chat and Executor (user interaction / automation)
   - Task agents: Specialized workflows (scheduling, suggestions, etc.)

2. **Shared Tools**: Both orchestrators use same workflow invocation tools
   - Located in `agents/shared/`
   - Provides consistent interface to task agents

3. **Task Agent Independence**: Each task agent:
   - Has its own tools and state
   - Can be tested in isolation
   - Can be called by any orchestrator

4. **No Circular Dependencies**:
   - Orchestrators → call → Shared tools → invoke → Task agents
   - Task agents never import orchestrators
