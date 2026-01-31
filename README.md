# Agent Development Environment

A standard set of tools, workflows, and documentation for AI-assisted development. Use this as a **submodule** in your projects to get consistent validation, environment setup, and AI workflows.

## Quick Start: Create a New Project

```bash
# 1. Clone this repo
git clone https://github.com/charojo/agent-dev-environment.git
cd agent-dev-environment

# 2. Create your project (sibling directory)
./bin/ADE_create_project.sh --name "my-app" --prompt "A web app for task management"
```

### What the script does:

1. **Creates project directory** — `../my-app/`
2. **Runs `git init`** — Initializes a new git repository
3. **Adds `agent_env` submodule** — Links this repo as a submodule
4. **Copies templates** — `config.toml`, `REQUIREMENTS.md`, etc.
5. **Runs `configure.py`** — Sets up workflows in `.agent/workflows/`
6. **Installs `README.agent.md`** — Next steps guide
7. **Creates initial commit** — Clean starting point

Basically, it is ready to push but is up to the user to create GitHub or other services. You can also run configure.py interactively to setup various standard configurations

### What you get:

```
my-app/
├── agent_env/          # This repo (submodule)
├── README.agent.md     # ⚡ Next steps - START HERE
├── config.toml         # Project configuration
├── REQUIREMENTS.md     # Feature requirements
├── ISSUES.md           # Known issues
├── PLANS.md            # Development roadmap
└── .agent/workflows/   # AI assistant workflows
```

### After running create-project:

```bash
cd ../my-app

# Read the next steps guide
cat README.agent.md

# Configure your project (interactive)
./agent_env/bin/configure.py --interactive

# Setup environment
./agent_env/bin/ADE_ensure_env.sh
```

### Adopt an Existing Project

```bash
./bin/ADE_create_project.sh --adopt /path/to/existing-project
```

This adds `agent_env` and `README.agent.md` to an existing project without overwriting your files.

### What You Get

When you run `./agent_env/bin/ADE_ensure_env.sh` in your project:

| Component | Description |
|-----------|-------------|
| **Python environment** | `.venv/` with dependencies from `pyproject.toml` |
| **Node environment** | `node_modules/` if web features enabled |
| **AI Workflows** | `.agent/workflows/` for AI assistants |
| **Validation** | Linting, tests, security checks |

## Working directly with this project (not the created one)

### Testing

```bash
# Run all tests
uv run pytest

# Run create-project E2E tests (creates real projects)
uv run pytest tests/test_create_project.py -v

# Keep a test project for exploration
uv run pytest tests/test_create_project.py::TestCreateProjectE2EIntegration::test_e2e_project_structure --keep -v -s
```

### Project Structure

```
agent-dev-environment/
├── bin/                    # Scripts
│   ├── ADE_create_project.sh   # Create/adopt projects
│   ├── ADE_ensure_env.sh       # Environment setup
│   ├── validate.sh             # Run validation
│   └── configure.py            # Interactive configuration
├── config/
│   ├── templates/          # Templates for new projects
│   ├── presets/            # Linter configs (ruff, eslint)
│   └── policy.toml         # Operation permissions
├── .agent/workflows/       # AI workflow instructions
├── docs/                   # Documentation
└── tests/                  # Test suite
```

### Configuration

The **Triple-Layer Configuration** system:

1. **Project Level (`config.toml`)** — Language and feature toggles
2. **Workflow Level (`.agent/workflows/*.md`)** — AI assistant instructions
3. **Shell Level (`bin/*.sh`)** — Bridge scripts

Interactive configuration:
```bash
./bin/configure.py
```

### Workflows

AI assistants look in `.agent/workflows/` for task instructions:

- `validate-ade.md` — Run tests and validation
- `cleanup-ade.md` — Clean build artifacts
- `architecture-ade.md` — Project structure reference
- `security-review-ade.md` — Security audit checklist

### Documentation

- [HOWTO_UseAgentDev.md](docs/HOWTO_UseAgentDev.md) — Comprehensive development guide

## License

Permissive and business friendly. You can use this project in your projects without any restrictions.

MIT License — see [LICENSE](LICENSE) for details.  
Copyright (c) 2025-2026 MyHeadwave LLC
