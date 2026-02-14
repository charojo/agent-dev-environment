# Agent Dev Environment — Requirements

## Project Automation Tooling (v0.0.5)

Requirements for the `create-project` script feature of **this** project.

---

## Functional Requirements

### REQ-001: Create-Project Script
**Priority:** P0  
**Description:** Provide a CLI script that generates git repositories from prompts.

**Acceptance Criteria:**
- [ ] `bin/create-project.sh "<prompt>"` creates a new repo
- [ ] Supports `--workspace <path>` option for output location
- [ ] Returns non-zero on failure with clear error message

**Test:** `tests/test_create_project.py`

---

### REQ-002: Submodule Integration
**Priority:** P0  
**Description:** Generated repos include agent_env as a git submodule.

**Acceptance Criteria:**
- [ ] `.gitmodules` added to generated repo
- [ ] Submodule points to this repository's URL
- [ ] `bin/validate.sh` available in generated repo

**Test:** `tests/test_create_project.py::test_submodule_added`

---

### REQ-003: Workspace Isolation
**Priority:** P0  
**Description:** Each project generation runs in an isolated workspace.

**Acceptance Criteria:**
- [ ] Workspace created at `/workspaces/<job-id>/`
- [ ] Structure: `repo/`, `logs/`, `artifacts/`
- [ ] File writes restricted to workspace boundary

**Test:** `tests/test_workspace.py`

---

### REQ-004: Policy Engine
**Priority:** P1  
**Description:** Gate risky operations via policy configuration.

**Acceptance Criteria:**
- [ ] `config/policy.toml` defines allowed/blocked operations
- [ ] Package installs require approval
- [ ] Network calls blocked by default

**Test:** `tests/test_policy.py`

---

### REQ-005: Structured Plan Output
**Priority:** P1  
**Description:** Script produces inspectable plan before execution.

**Acceptance Criteria:**
- [ ] `--dry-run` flag outputs plan without executing
- [ ] Plan saved as `logs/<job-id>/plan.json`

**Test:** `tests/test_create_project.py::test_dry_run`

---

## Non-Functional Requirements

### NFR-001: Generation Time
**Target:** < 30 seconds for scaffold (excluding agent response time)

### NFR-002: Clean Test Runs
**Target:** All tests pass without leftover files  
**Measurement:** CI runs in isolated temp directories

---

## References

- [PLANS.md](PLANS.md)
- [ISSUES.md](ISSUES.md)
