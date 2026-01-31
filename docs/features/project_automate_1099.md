# Example Project: 1099 Contractor Planner

This document specifies an **example "other" project** that will be generated using the `create-project` tooling from agent-dev-environment.

> See [project_automation.md](project_automation.md) for the tooling roadmap.

---

## Project Overview

**Prompt:**
> "Create a local-first tool for 1099 contractors to plan taxes and expenses in NY, focused on cash flow safety."

**Target Audience:**
- 1099 contractors
- Consultants
- Fractional managers
- Late-career professionals transitioning from W-2

---

## Functional Scope

### Inputs
- Income streams (hourly, contract, variable)
- Expense categories (health insurance, equipment, home office, travel)
- Filing status (simplified)
- State (NY initially)

### Outputs
- Estimated quarterly taxes
- Effective tax rate
- Cash-flow view (monthly)
- "Safe to spend" estimate

### Scenarios
- Current year actuals
- Projected next 6–12 months
- Comparison against prior W-2 baseline

---

## Tech Stack (Intentional Constraints)

| Layer | Choice |
|-------|--------|
| Language | Python |
| UI | CLI first, web optional |
| Storage | SQLite or flat files |
| External APIs | None required |

---

## Success Criteria

This generated project is successful if:

1. Repo is generated in < 5 minutes
2. Code is readable and idiomatic
3. App runs locally without modification
4. Financial logic is explicit and inspectable
5. `agent_env/bin/validate.sh` passes

---

## Example Generated Structure

```
1099-planner/
├── .git/
├── .gitmodules           # → agent_env submodule
├── agent_env/            # Submodule
├── src/
│   ├── main.py
│   ├── income.py
│   ├── expenses.py
│   └── tax_calc.py
├── tests/
│   └── test_tax_calc.py
├── docs/
│   ├── vision.md
│   └── architecture.md
└── README.md
```

---

## References

- [Project Automation Tooling](project_automation.md) — The feature that generates this project
- [PLANS.md](../../PLANS.md) — Current development focus for agent-dev-environment
