---
description: How to maintain path integrity and avoid absolute paths in documentation
---

This workflow ensures that all project documentation (files in `docs/`) uses relative paths for internal links and assets, maintaining portability and preventing environment-specific errors.

## Principles

1.  **Portability**: Documentation must be viewable and functional on any machine (Local, WSL, GitHub, etc.).
2.  **Schema Distinction**:
    *   **Relative Paths**: MUST be used in all permanent project documentation (e.g., `[link](./other.md)`, `![image](../assets/img.png)`).
    *   **Absolute Paths**: ONLY allowed in transient agent artifacts (implementation plans, walkthroughs) stored in the `.gemini/` directory, using the `file:///` URI scheme.

## Steps

1.  **Check for Absolute Paths**:
    Before committing or finalizing any design document, run the path enforcement script:
    ```bash
    uv run python bin/enforce_relative_paths.py
    # OR if in submodule: uv run python agent_env/bin/enforce_relative_paths.py
    ```

2.  **Fixing Violations**:
    If absolute paths are found (e.g., starting with `/home/` or `file:///home/`):
    - Identify the target file's location relative to the current document.
    - Replace the absolute path with a standard markdown relative path.
    - **Example**: Replace an absolute path like `file:///PATH/TO/target.md` with `./target.md`.

3.  **Cross-Document Linking**:
    - Use `./` for files in the same directory.
    - Use `../` to traverse up the directory tree.
    - Always verify the link by clicking it in your editor or checking the rendered markdown.

4.  **Diagrams and Assets**:
    - **Visual Standard**: All diagrams MUST use the **Graphviz DOT** standard for source files (`.dot`) and **SVG** for rendering.
    - **Mermaid Warning**: Mermaid code blocks (`` `mermaid ``) DO NOT render in the repository environment and should be avoided in permanent documentation.
    - **Registry**: Place `.dot` source files in `docs/assets/diagrams/`.
    - **Generation**: After modifying any `.dot` file, you MUST generate/update the corresponding PNG:
      ```bash
      uv run python bin/generate_diagrams.py
      # OR if in submodule: uv run python agent_env/bin/generate_diagrams.py
      ```
    - **Linking**: Embed diagrams using relative SVG paths and provide a link to the DOT source:
      ```markdown
      ![Diagram Name](../assets/diagrams/name.svg)
      *[Source: name.dot](../assets/diagrams/name.dot)*
      ```
