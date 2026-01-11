# Agent Development Environment

A standard set of tools, workflows, and documentation for AI-assisted development. This repository acts as the "Kernel" for agentic projects, providing a consistent interface for validation, environment setup, and architectural planning.

## Architecture

This environment is designed to be included in projects (via git submodule or subtree) at `.agent/` or `agent_env/`.

*   **bin/**: Universal scripts (`validate.sh`, `ensure_env.sh`) that bridge the generic agent interface to project-specific tools.
*   **config/**: Standard configuration templates (`ruff.toml`, `eslintrc.json` in `presets/`).
*   **docs/**: Methodology documentation ("How to work with Agents"), including Architecture and Ecosystem guides.
*   **workflows/**: Markdown-driven SOPs for agents (`validate.md`, `security-review.md`).

## Integration

1.  **Submodule**: Add this repo as a submodule (e.g., at `agent_env/` or `.agent/`).
2.  **Standalone**: Use it as the base for a new project.

## Configuration

The environment uses a **Triple-Layer Configuration** system:
1.  **Project Level (`config.toml`)**: Core feature and language toggles.
2.  **Workflow Level (`workflows/*.md`)**: Standard Operating Procedures for agents.
3.  **Shell Level (`bin/*.sh`)**: Generic bridge scripts that adapt to the project state.

Use the interactive wizard to set up your project:
```bash
./bin/configure.py --interactive
# OR
./bin/validate.sh --configure
```

This will help you enable/disable:
- **Languages**: Python, TypeScript/JS.
- **Features**: Advanced Documentation (Doxygen, PDF generation, Graphviz).
- **Tooling**: Automatic PATH integration.

## Workflows

The agent looks in `workflows/` for instructions on how to perform tasks.

*   `workflows/core/validate.md`: Run tests and validation.
*   `workflows/core/cleanup.md`: Clean build artifacts and logs.
*   `workflows/core/architecture.md`: Reference for project structure.

## Documentation

- [HOWTO_UseAgentDev.md](docs/HOWTO_UseAgentDev.md): Comprehensive development guide, architecture, and ecosystem reference.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
Copyright (c) 2025-2026 MyHeadwave LLC
