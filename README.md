# Agent Development Environment

A standard set of tools, workflows, and documentation for AI-assisted development. This repository acts as the "Kernel" for agentic projects, providing a consistent interface for validation, environment setup, and architectural planning.

## Architecture

This environment is designed to be included in projects (via git submodule or subtree) at `.agent/` or `agent_env/`.

*   **bin/**: Universal scripts (`validate.sh`, `ensure_env.sh`) that bridge the generic agent interface to project-specific tools.
*   **config/**: Standard configuration templates (`ruff.toml`, `.eslintrc`).
*   **docs/**: Methodology documentation ("How to work with Agents").
*   **workflows/**: Markdown-driven SOPs for agents (`validate.md`, `security-review.md`).

## Integration

1.  Copy or Submodule this repo into your project.
2.  Create a `agent_env/config.toml` in your project root to configure the adapter.
3.  Run `agent_env/bin/validate.sh` to veriy the setup.

## Workflows

The agent looks in `workflows/` for instructions on how to perform tasks.

*   `workflows/core/validate.md`: Run tests.
*   `workflows/core/cleanup.md`: Clean artifacts.
