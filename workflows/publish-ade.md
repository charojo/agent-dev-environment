---
description: Push new/existing project to GitHub with best practices (Hooks, Branch Protection, CI)
---

1.  **Gather Project Info**
    Identify the repository name, description, and visibility.
    - Repository Name: (e.g., mesh-sim)
    - Description: (e.g., Mesh network simulation framework)
    - Visibility: (public or private)

2.  **Initialize Git Infrastructure**
    Ensure `.pre-commit-config.yaml` exists with Ruff configuration.
    // turbo
    cat <<EOF > .pre-commit-config.yaml
    repos:
      - repo: https://github.com/astral-sh/ruff-pre-commit
        rev: v0.1.0
        hooks:
          - id: ruff
            args: [--fix, --exit-non-zero-on-fix]
          - id: ruff-format
    EOF

3.  **Setup GitHub CI**
    Configure GitHub Actions to run the validation script.
    // turbo
    mkdir -p .github/workflows && cat <<EOF > .github/workflows/ci.yml
    name: CI
    on: [push, pull_request]
    jobs:
      validate:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v3
          - name: Set up Python
            uses: actions/setup-python@v4
            with:
              python-version: '3.10'
          - name: Install dependencies
            run: |
              curl -LsSf https://astral.sh/uv/install.sh | sh
              uv sync
          - name: Run Validation
            run: ./agent_env/bin/validate.sh --full
    EOF

4.  **Publish to GitHub**
    Check for existing remote and handle accordingly.
    // turbo
    CURRENT_BRANCH=\$(git branch --show-current)
    if [ -z "\$CURRENT_BRANCH" ]; then
        CURRENT_BRANCH="main" 
    fi
    
    # Check if origin exists
    if git remote | grep origin > /dev/null; then
      echo "Remote 'origin' exists. Pushing code..."
      git add .pre-commit-config.yaml .github/workflows/ci.yml
      git commit -m "chore: add pre-commit hooks and CI workflow" || echo "No changes to commit"
      
      # Push to the current branch
      git push -u origin "\$CURRENT_BRANCH"

      # If main/master is protected, we might need a PR, but for initial setup, let's try direct push first.
      # If direct push fails, then we fallback to PR logic (advanced).
      # For now, we assume the user has rights to push to their own new repo.
      
    else
      echo "No remote 'origin' found."
      # Prompt for visibility if not set
      if [ -z "\$VISIBILITY" ]; then
        echo "Select repository visibility:"
        select vis in "public" "private"; do
          VISIBILITY=\$vis
          break
        done
      fi
      
      echo "Creating new repository (Visibility: \$VISIBILITY)..."
      
      # Try to create. If it fails (e.g. name exists), we catch it.
      if gh repo create --source=. --remote=origin --push --description "Mesh network simulation framework" --"\$VISIBILITY"; then
         echo "Repository created successfully."
      else
         echo "Repo creation failed. It might already exist."
         read -p "Does the repo already exist on GitHub? (y/n) " exists
         if [[ "\$exists" == "y" ]]; then
            read -p "Enter GitHub URL (e.g. https://github.com/user/repo.git): " repo_url
            git remote add origin "\$repo_url"
            git push -u origin "\$CURRENT_BRANCH"
         else
            echo "Please troubleshoot 'gh repo create' manually."
            exit 1
         fi
      fi
    fi

5.  **Enable Branch Protection**
    Apply best practice protection to the main branch.
    // turbo
    gh api -X PUT /repos/:owner/:repo/branches/main/protection \\
      -H "Accept: application/vnd.github.v3+json" \\
      -f '{"required_status_checks":{"strict":true,"contexts":["validate"]},"enforce_admins":true,"required_pull_request_reviews":{"required_approving_review_count":1},"restrictions":null}'
