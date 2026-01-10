# HOWTO: Agent Workflows

This document outlines how to effectively work with the AI agents in this project and lists the available automated workflows.

## Requesting Work

To request work from an agent, simply describe your task in natural language in the chat interface. The agents follow a structured loop:

1.  **Plan**: The agent will analyze your request and the codebase, then propose an `implementation_plan.md`. You should review this plan carefully.
2.  **Execute**: Once the plan is approved, the agent will execute the changes, modifying code and running commands.
3.  **Verify**: The agent will verify the changes using tests or checks and create a `walkthrough.md` to demonstrate the results.

### Tips for Best Results
- Be specific about what you want.
- Reference specific files or error messages.
- If a task is complex, ask for a plan first.

## Agent Workflows

Workflows are pre-defined sets of instructions that agents can access to perform common tasks consistently. You can trigger these by name or by asking for the specific task.

### Available Workflows

<!-- WORKFLOWS_START -->
| Command | Description |
| :--- | :--- |
| `/add-scene` | How to add a new scene to the Papeterie Engine |
| `/architecture` | Architectural Changes and Big Feature Implementations |
| `/cleanup` | Cleanup system files, caches, and logs |
| `/css-review` | Review CSS compliance and design system usage before merging |
| `/design-planning` | Design and Planning tasks (UI/UX, System Design) |
| `/docs-path-integrity` | How to maintain path integrity and avoid absolute paths in documentation |
| `/security-review` | Perform a basic security review of the project |
| `/ux-review` | Perform a UX and Accessibility Review of the application |
| `/validate` | Run exhaustive QA and full project validation |
<!-- WORKFLOWS_END -->

## Automatic Updates

This list is automatically updated by `scripts/update_workflow_docs.py`.
