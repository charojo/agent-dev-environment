---
description: Run exhaustive QA and full project validation
model: gemini-1.5-pro, gemini-2.0-flash
---
1. Run Validation (Select a Tier)

- **Fast** (Changeset only, ~5s):
// turbo
./agent_env/bin/validate.sh --fast

- **Medium** (File-level, formatting, ~10s):
// turbo
./agent_env/bin/validate.sh --medium

- **Full** (All Unit/Integration, E2E, ~90s) - *Recommended for Pre-Commit*:
// turbo
./agent_env/bin/validate.sh --full

- **Exhaustive** (Parallel execution, Max coverage, ~5m) - *Recommended for Pre-Merge*:
// turbo
./agent_env/bin/validate.sh --exhaustive

2. Options

- Include Live API tests: `--live`
- Skip Auto-fix: `--no-fix`
- E2E Only: `--e2e-only`

3. Troubleshooting

- If backend tests show "1 passed" instead of full count, check `analyze.sh` section parsing.
- 2 tests are always skipped (live API tests) unless `--live` is used.
- Parallel mode may reveal flaky tests that pass in serial mode.
