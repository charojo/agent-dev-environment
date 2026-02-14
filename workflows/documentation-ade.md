---
description: Unified Documentation Workflow (Path Validation, Diagrams, API Docs)
---

This workflow is the single point of entry for maintaining project documentation integrity and generating assets.

## Core Pillars

1.  **Path Integrity**: Ensures all `docs/` files use relative paths.
2.  **Diagram Generation**: Compiles Graphviz `.dot` files to `.svg`.
3.  **Doc Extraction**: Extracts `## @DOC` blocks from source code.
4.  **API Documentation**: Generates Doxygen/TypeDoc if applicable.

## Steps

// turbo-all

1.  **Ensure Documentation Coverage**:
    - Scan all source files (`.py`, `.js`, `.ts`, `.sh`) for `## @DOC` headers.
    - If a file is missing a header, create one with a meaningful description using the correct syntax (`#` or `//`).

2.  **Ensure README Exists**:
    - Check if `README.md` exists in the project root.
    - If missing, create a best-effort README describing the project structure and usage.

3.  **Enforce Path Portability**:
    ```bash
    uv run python agent_env/bin/ADE_enforce_relative_paths.py
    ```

4.  **Generate Diagrams and Fix Assets**:
    - Compile diagrams (DOT and Mermaid) using figure numbering and descriptive names.
    - Ensure all Mermaid source code is moved to `docs/assets/diagrams/` as `.mmd` files.
    - Update Markdown files to use `figure <num>: <caption text>` format with links to SVG and source.
    ```bash
    uv run python agent_env/bin/ADE_generate_diagrams.py
    ```

5.  **Validate Diagram Convention**:
    ```bash
    uv run pytest agent_env/tests/test_diagram_convention.py
    ```

6.  **Execute Document Extraction & API Docs**:
    This generates the design spec and updates Doxygen/TypeDoc.
    ```bash
    uv run python agent_env/bin/ADE_document.py
    ```

6.  **Update Workflow Registry**:
    This updates cross-references in manual documents.
    ```bash
    uv run python agent_env/bin/ADE_update_workflow_docs.py
    ```

## Verification
- Check `docs/gen/` for updated `DESIGN_SPEC.md` and `doxygen/`.
- Verify `.svg` files in `docs/assets/diagrams/` match their `.dot` sources.