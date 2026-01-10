# Agent Environment Architecture

## Overview

The **Agent Development Environment** acts as a "Kernel" or "Adapter" that sits between a generic AI Agent and a specific project repository. It provides a standardized interface for agents to discover, validate, and understand the codebase, regardless of the underlying technology stack.

## Core Concepts

### 1. The Adapter Pattern

Agents work best when they have a consistent set of tools ("affordances"). Just as an Operating System provides standard syscalls (open, read, write) to applications, this environment provides standard "syscalls" to the agent:

*   **validate**: "Is the project healthy?"
*   **ensure_env**: "Is the environment set up?"
*   **workflows**: "How do I perform complex tasks?"

This allows the same Agent to work on a Python backend, a Node.js frontend, or a Go service, as long as the adapter is configured correctly.

### 2. Dual-Mode Execution

This repository is designed to run in two modes:

*   **Standalone Mode**: When developing the agent environment itself (e.g., this repo). The scripts detect they are at the root.
*   **Submodule Mode**: When included as a library (e.g., `git submodule add ... agent_env`). The scripts detect they are in a subdirectory and verify the *host* project.

## Configuration Architecture

The repository uses a layered configuration approach to separate "Build" concerns from "Runtime/Adapter" concerns.

### Layer 1: Repository Build (`pyproject.toml`)
*   **Role**: Defines how to build and install the *Agent Environment itself*.
*   **Scope**: Internal to this repository.
*   **Usage**: Used by `uv`, `pip`, `pytest` to install dependencies needed for the *scripts* (like `pytest-testmon` or `ruff`).
*   **Location**: Always in the root of the `agent-dev-environment`.

### Layer 2: Adapter Configuration (`config.toml`)
*   **Role**: Defines how the Agent Environment interacts with the *Host Project*.
*   **Scope**: The Host Project.
*   **Usage**: Used by `bin/validate.sh` and other scripts to know:
    *   What is the project name?
    *   What command runs the fast tests? `pytest`? `npm test`? `cargo test`?
    *   Where are the source files?
*   **Location**: 
    *   **In Standalone Mode**: `config.toml` in the `agent-dev-environment` root.
    *   **In Submodule Mode**: `config.toml` in the *Host Project's* root.

### Layer 3: Template (`config.example.toml`)
*   **Role**: Documentation/Starter file.
*   **Scope**: Public API.
*   **Usage**: Users copy this to `config.toml` when first integrating the environment.

## Logic Flow

When `bin/validate.sh` runs:

1.  **Resolution**: Checks `pyproject.toml` location to determine if running Standalone or Submodule.
2.  **Environment**: Runs `bin/ensure_env.sh` to install dependencies defined in `pyproject.toml`.
3.  **Configuration**: Load `config.toml` to determine which test commands to run.
4.  **Execution**: Executes the project-specific commands (e.g., `uv run pytest`).
