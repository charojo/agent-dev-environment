# Agent Dev Environment — Issues

## Open Issues

### ISSUE-001: Test Workspace Cleanup
**Status:** � Ready  
**Severity:** Medium  
**Component:** Testing

**Description:**  
Test runs for `create-project` will generate temp git repos. Need pytest fixtures to ensure cleanup.

**Action:**
- Add `temp_workspace` fixture using `tmp_path`
- Verify no orphan files after test suite

---

### ISSUE-002: Policy File Format
**Status:** 🟡 In Design  
**Severity:** Medium  
**Component:** `config/policy.toml`

**Description:**  
Need to define schema for policy configuration. Questions:
- Allow-list vs block-list approach?
- Per-command granularity or categories?
- How to handle user overrides?

---

### ISSUE-003: Submodule URL Configuration
**Status:** � In Design  
**Severity:** Low  
**Component:** `bin/create-project.sh`

**Description:**  
Script needs to know agent_env's git URL. Options:
1. Hardcoded URL
2. Config file
3. Derive from current remote

---

## Resolved Issues

| ID | Summary | Resolution | Version |
|----|---------|------------|---------|
| — | (none yet) | — | — |

---

## References

- [PLANS.md](PLANS.md)
- [REQUIREMENTS.md](REQUIREMENTS.md)
