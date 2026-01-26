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

1.  **Enforce Path Portability**:
    ```bash
    uv run python agent_env/bin/ADE_enforce_relative_paths.py
    ```

2.  **Generate Diagrams and Assets**:
    This step compiles all diagrams and updates links in the source code.
    ```bash
    uv run python agent_env/bin/ADE_generate_diagrams.py
    ```

3.  **Execute Document Extraction & API Docs**:
    This generates the design spec and updates Doxygen/TypeDoc.
    ```bash
    uv run python agent_env/bin/ADE_document.py
    ```

4.  **Update Workflow Registry**:
    (Optional) Updates cross-references in manual documents.
    ```bash
    uv run python agent_env/bin/ADE_update_workflow_docs.py
    ```

## Verification
- Check `docs/gen/` for updated `DESIGN_SPEC.md` and `doxygen/`.
- Verify `.svg` files in `docs/assets/diagrams/` match their `.dot` sources.
