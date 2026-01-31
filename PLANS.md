# Agent Dev Environment — Plans

## Current Focus: Project Automation Tooling (v0.0.4)

Build the **create-project** infrastructure that bootstraps new repositories with agent_env as a submodule.

> This project provides general services for "other" projects. See [docs/features/](docs/features/) for specific feature roadmaps.

---

## Phase 1 — Create-Project Script

### Goal
Deliver `bin/create-project.sh` that takes a prompt and generates a ready-to-use git repository.

### Components to Build

| Component | Description | Status |
|-----------|-------------|--------|
| `bin/ADE_create_project.sh` | CLI entry point | ✅ Done |
| `config/policy.toml` | Allowed operations config | ✅ Done |
| Workspace isolation | `/workspaces/<job-id>/` structure | ✅ Done |
| Agent system prompt | Project generation instructions | 🔴 TODO |

### Architecture

```
bin/create-project.sh
         |
         v
[ Orchestrator Logic ]
         |
         +--→ Validate prompt
         +--→ Create workspace
         +--→ git init + add agent_env submodule
         +--→ Invoke agent with system prompt
         +--→ Apply policy checks
         +--→ Commit + log
```

---

## Testing Strategy

Each component needs coverage:

```bash
tests/
├── test_create_project.py    # Integration test for full workflow
├── test_workspace.py         # Isolation tests
├── test_policy.py            # Policy engine tests
└── test_orchestrator.py      # Plan parsing tests
```

---

## References

- [Project Automation Feature](docs/features/project_automation.md)
- [1099 Example Project](docs/features/project_automate_1099.md)
- [REQUIREMENTS.md](REQUIREMENTS.md)
- [ISSUES.md](ISSUES.md)
