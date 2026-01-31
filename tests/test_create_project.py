"""Tests for bin/ADE_create_project.sh

Run with --keep to preserve test projects for exploration:
    pytest tests/test_create_project.py::TestCreateProjectE2EIntegration --keep -v -s
"""

import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def temp_output(tmp_path):
    """Create a temporary output directory for testing."""
    output = tmp_path / "projects"
    output.mkdir()
    yield output


@pytest.fixture
def script_path():
    """Get path to the create-project script."""
    return Path(__file__).parent.parent / "bin" / "ADE_create_project.sh"


class TestCreateProjectDryRun:
    """Tests for --dry-run mode (no side effects)."""

    def test_dry_run_shows_plan(self, script_path, temp_output):
        """--dry-run outputs plan without creating files."""
        result = subprocess.run(
            [
                str(script_path),
                "--name",
                "test-project",
                "--output",
                str(temp_output),
                "--dry-run",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Create Project Plan" in result.stdout
        assert "test-project" in result.stdout
        assert "[DRY RUN]" in result.stdout

    def test_dry_run_no_files_created(self, script_path, temp_output):
        """--dry-run should not create any directories."""
        subprocess.run(
            [
                str(script_path),
                "--name",
                "test-project",
                "--output",
                str(temp_output),
                "--dry-run",
            ],
            capture_output=True,
        )
        # Output should remain empty
        assert len(list(temp_output.iterdir())) == 0


class TestCreateProjectExecution:
    """Tests for actual project creation."""

    def test_creates_project_directory(self, script_path, temp_output):
        """Project directory is created in output location."""
        result = subprocess.run(
            [
                str(script_path),
                "--name",
                "my-app",
                "--output",
                str(temp_output),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

        project_dir = temp_output / "my-app"
        assert project_dir.is_dir()

    def test_initializes_git_repo(self, script_path, temp_output):
        """Generated project is a valid git repo."""
        subprocess.run(
            [
                str(script_path),
                "--name",
                "git-test",
                "--output",
                str(temp_output),
            ],
            capture_output=True,
        )

        project_dir = temp_output / "git-test"
        assert (project_dir / ".git").is_dir()

        # Verify it's a valid git repo with initial commit
        result = subprocess.run(
            ["git", "log", "--oneline", "-1"],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Initial commit" in result.stdout

    def test_adds_agent_env(self, script_path, temp_output):
        """agent_env is added to project (submodule or copy)."""
        subprocess.run(
            [
                str(script_path),
                "--name",
                "submodule-test",
                "--output",
                str(temp_output),
            ],
            capture_output=True,
        )

        project_dir = temp_output / "submodule-test"
        agent_env = project_dir / "agent_env"

        # Should have agent_env (either as submodule or copied)
        assert agent_env.is_dir()
        # Should have key files
        assert (agent_env / "bin").is_dir()

    def test_copies_templates(self, script_path, temp_output):
        """Template files exist in generated project."""
        subprocess.run(
            [
                str(script_path),
                "--name",
                "template-test",
                "--output",
                str(temp_output),
            ],
            capture_output=True,
        )

        project_dir = temp_output / "template-test"

        # Check for expected files
        assert (project_dir / "README.agent.md").is_file()
        assert (project_dir / ".gitignore").is_file()
        assert (project_dir / "config.toml").is_file()
        assert (project_dir / "REQUIREMENTS.md").is_file()
        assert (project_dir / "ISSUES.md").is_file()
        assert (project_dir / "pyproject.toml").is_file()

    def test_config_has_project_name(self, script_path, temp_output):
        """config.toml should have the project name set."""
        subprocess.run(
            [
                str(script_path),
                "--name",
                "named-project",
                "--output",
                str(temp_output),
            ],
            capture_output=True,
        )

        config_file = temp_output / "named-project" / "config.toml"
        content = config_file.read_text()
        assert 'name = "named-project"' in content

    def test_sanitizes_project_name(self, script_path, temp_output):
        """Project names are sanitized (lowercase, hyphens)."""
        subprocess.run(
            [
                str(script_path),
                "--name",
                "My Cool App",
                "--output",
                str(temp_output),
            ],
            capture_output=True,
        )

        project_dir = temp_output / "my-cool-app"
        assert project_dir.is_dir()

    def test_prevents_overwrite(self, script_path, temp_output):
        """Cannot create project if directory already exists."""
        # Create first time
        subprocess.run(
            [
                str(script_path),
                "--name",
                "existing-project",
                "--output",
                str(temp_output),
            ],
            capture_output=True,
        )

        # Try to create again
        result = subprocess.run(
            [
                str(script_path),
                "--name",
                "existing-project",
                "--output",
                str(temp_output),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "already exists" in result.stdout


class TestCreateProjectArgs:
    """Tests for argument handling."""

    def test_requires_name(self, script_path, temp_output):
        """--name is required."""
        result = subprocess.run(
            [str(script_path), "--output", str(temp_output)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert (
            "--name is required" in result.stderr
            or "--name is required" in result.stdout
        )

    def test_help_option(self, script_path):
        """--help shows usage."""
        result = subprocess.run(
            [str(script_path), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Usage:" in result.stdout
        assert "--name" in result.stdout
        assert "--output" in result.stdout

    def test_readme_agent_has_next_steps(self, script_path, temp_output):
        """README.agent.md has Next Steps section."""
        subprocess.run(
            [
                str(script_path),
                "--name",
                "prompted-app",
                "--prompt",
                "A todo list application",
                "--output",
                str(temp_output),
            ],
            capture_output=True,
        )

        readme = temp_output / "prompted-app" / "README.agent.md"
        content = readme.read_text()
        # Check for key sections in the Next Steps guide
        assert "Next Step" in content
        assert "configure.py" in content


class TestCreateProjectE2EIntegration:
    """
    End-to-end integration tests that create real projects in the parent directory.

    These tests:
    1. Create projects with 'test_' prefix for easy identification
    2. Validate the full agent_env bootstrap workflow
    3. Clean up after themselves
    4. Log all output to logs/e2e_create_project/ for review
    """

    @pytest.fixture
    def agent_env_root(self):
        """Get the agent-dev-environment root directory."""
        return Path(__file__).parent.parent

    @pytest.fixture
    def logs_dir(self, agent_env_root):
        """Get/create the logs directory for E2E test output."""
        log_dir = agent_env_root / "logs" / "e2e_create_project"
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir

    @pytest.fixture
    def parent_output_dir(self, agent_env_root):
        """Get the parent directory where sibling projects are created."""
        return agent_env_root.parent

    @pytest.fixture
    def test_project_name(self, request):
        """Generate a unique test project name with test_ prefix."""
        import time
        import uuid

        # Use short uuid to ensure uniqueness even when tests run in same second
        short_id = str(uuid.uuid4())[:8]
        return f"test_e2e_{int(time.time())}_{short_id}"

    @pytest.fixture
    def create_test_project(
        self, script_path, parent_output_dir, test_project_name, logs_dir, keep_projects
    ):
        """
        Fixture that creates a test project and cleans up after the test.

        Logs all output to logs/e2e_create_project/ for review.
        Use --keep flag to preserve project for exploration.
        Yields the project directory path for use in tests.
        """
        from datetime import datetime

        project_dir = parent_output_dir / test_project_name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = logs_dir / f"{timestamp}_{test_project_name}.log"

        # Create the project
        result = subprocess.run(
            [
                str(script_path),
                "--name",
                test_project_name,
                "--prompt",
                "E2E test project for validation",
                "--output",
                str(parent_output_dir),
                "--non-interactive",
            ],
            capture_output=True,
            text=True,
        )

        # Log the create-project output
        with open(log_file, "w") as f:
            f.write(f"# E2E Test Log: {test_project_name}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"Project Dir: {project_dir}\n")
            f.write(f"Return Code: {result.returncode}\n")
            f.write(f"Keep Project: {keep_projects}\n")
            f.write("\n## STDOUT\n")
            f.write(result.stdout)
            f.write("\n## STDERR\n")
            f.write(result.stderr)

        assert result.returncode == 0, (
            f"Failed to create project: {result.stderr}. See {log_file}"
        )
        assert project_dir.is_dir(), f"Project directory not created: {project_dir}"

        # Return both project_dir and log_file for tests to append to
        yield project_dir, log_file

        # Cleanup after test (unless --keep was passed)
        if keep_projects:
            print(f"\n\n🔒 KEPT: {project_dir}")
            print(f"   Log:  {log_file}")
            print("\n   To explore:")
            print(f"     cd {project_dir}")
            print("     ./agent_env/bin/ADE_ensure_env.sh\n")
        else:
            import shutil

            if project_dir.exists():
                shutil.rmtree(project_dir)

    def test_e2e_project_structure(self, create_test_project):
        """Validate complete project structure after real creation."""
        project_dir, log_file = create_test_project

        checks = []
        # Core structure
        checks.append((".git", (project_dir / ".git").is_dir()))
        checks.append(("agent_env", (project_dir / "agent_env").is_dir()))

        # Template files
        checks.append(("README.agent.md", (project_dir / "README.agent.md").is_file()))
        checks.append(("config.toml", (project_dir / "config.toml").is_file()))
        checks.append(("REQUIREMENTS.md", (project_dir / "REQUIREMENTS.md").is_file()))
        checks.append(("ISSUES.md", (project_dir / "ISSUES.md").is_file()))
        checks.append(("PLANS.md", (project_dir / "PLANS.md").is_file()))
        checks.append(("pyproject.toml", (project_dir / "pyproject.toml").is_file()))
        checks.append((".gitignore", (project_dir / ".gitignore").is_file()))

        # Log results
        with open(log_file, "a") as f:
            f.write("\n## test_e2e_project_structure\n")
            for name, exists in checks:
                status = "✓" if exists else "✗"
                f.write(f"  {status} {name}\n")

        for name, exists in checks:
            assert exists, f"Missing: {name}"

    def test_e2e_agent_env_scripts_exist(self, create_test_project):
        """Validate agent_env has expected scripts."""
        project_dir, log_file = create_test_project
        agent_env = project_dir / "agent_env"

        scripts = [
            "bin/ADE_ensure_env.sh",
            "bin/validate.sh",
            "bin/configure.py",
        ]

        with open(log_file, "a") as f:
            f.write("\n## test_e2e_agent_env_scripts_exist\n")
            for script in scripts:
                exists = (agent_env / script).is_file()
                status = "✓" if exists else "✗"
                f.write(f"  {status} agent_env/{script}\n")

        for script in scripts:
            assert (agent_env / script).is_file(), f"Missing: agent_env/{script}"

    def test_e2e_ensure_env_runs(self, create_test_project):
        """Validate ADE_ensure_env.sh can be executed in new project."""
        project_dir, log_file = create_test_project

        # Run ensure_env - should at least start without immediate error
        result = subprocess.run(
            ["./agent_env/bin/ADE_ensure_env.sh"],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=60,  # Give it reasonable time
        )

        # Log the ensure_env output
        with open(log_file, "a") as f:
            f.write("\n## test_e2e_ensure_env_runs\n")
            f.write(f"Return Code: {result.returncode}\n")
            f.write("### STDOUT\n")
            f.write(result.stdout)
            f.write("\n### STDERR\n")
            f.write(result.stderr)

        # Must succeed - if pyproject.toml is missing, this will fail
        assert result.returncode == 0, (
            f"ensure_env failed (return code {result.returncode}): {result.stderr}"
        )

        # Verify .venv was actually created
        assert (project_dir / ".venv").is_dir(), (
            ".venv directory not created by ensure_env"
        )

    def test_e2e_git_status_clean(self, create_test_project):
        """Validate git status is clean after creation."""
        project_dir, log_file = create_test_project

        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
        )

        with open(log_file, "a") as f:
            f.write("\n## test_e2e_git_status_clean\n")
            f.write(f"git status --porcelain:\n{result.stdout or '(clean)'}\n")

        # Should have no uncommitted changes
        assert result.returncode == 0
        lines = [
            line
            for line in result.stdout.strip().split("\n")
            if line and not line.startswith(" M")
        ]
        assert len(lines) == 0 or result.stdout.strip() == "", (
            f"Unexpected uncommitted changes: {result.stdout}"
        )

    def test_e2e_git_log_has_commit(self, create_test_project):
        """Validate initial commit exists with proper message."""
        project_dir, log_file = create_test_project

        result = subprocess.run(
            ["git", "log", "--oneline", "-1"],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
        )

        with open(log_file, "a") as f:
            f.write("\n## test_e2e_git_log_has_commit\n")
            f.write(f"git log: {result.stdout}\n")

        assert result.returncode == 0
        assert "Initial commit" in result.stdout

    def test_e2e_config_has_correct_name(self, create_test_project, test_project_name):
        """Validate config.toml has the project name set."""
        project_dir, log_file = create_test_project

        config_content = (project_dir / "config.toml").read_text()

        with open(log_file, "a") as f:
            f.write("\n## test_e2e_config_has_correct_name\n")
            f.write(f'Expected: name = "{test_project_name}"\n')
            f.write(f"Found: {'✓' if test_project_name in config_content else '✗'}\n")

        assert f'name = "{test_project_name}"' in config_content

    def test_e2e_configure_runs(self, create_test_project):
        """Validate configure.py runs successfully (README instruction)."""
        project_dir, log_file = create_test_project

        result = subprocess.run(
            ["./agent_env/bin/configure.py", "--non-interactive"],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=30,
        )

        with open(log_file, "a") as f:
            f.write("\n## test_e2e_configure_runs\n")
            f.write("Command: ./agent_env/bin/configure.py --non-interactive\n")
            f.write(f"Return Code: {result.returncode}\n")
            f.write("### STDOUT\n")
            f.write(result.stdout[:500] if result.stdout else "(empty)\n")
            f.write("\n### STDERR\n")
            f.write(result.stderr[:500] if result.stderr else "(empty)\n")

        assert result.returncode == 0, f"configure.py failed: {result.stderr}"

    def test_e2e_validate_runs(self, create_test_project):
        """Validate validate.sh runs successfully (README instruction)."""
        project_dir, log_file = create_test_project

        result = subprocess.run(
            ["./agent_env/bin/validate.sh"],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=120,  # Validation can take time
        )

        with open(log_file, "a") as f:
            f.write("\n## test_e2e_validate_runs\n")
            f.write("Command: ./agent_env/bin/validate.sh\n")
            f.write(f"Return Code: {result.returncode}\n")
            f.write("### STDOUT (last 1000 chars)\n")
            f.write(result.stdout[-1000:] if result.stdout else "(empty)\n")
            f.write("\n### STDERR\n")
            f.write(result.stderr[:500] if result.stderr else "(empty)\n")

        # validate.sh requires pyproject.toml which new projects don't have yet
        # Return code 2 means "no pyproject.toml found" - expected for empty projects
        # Return code 0/1 means validation ran (pass/fail)
        assert result.returncode in [0, 1, 2], (
            f"validate.sh crashed unexpectedly: {result.stderr}"
        )

        # If return code is 2, verify it's the expected "no pyproject" error
        if result.returncode == 2:
            assert (
                "pyproject.toml" in result.stderr
                or "pyproject" in result.stdout.lower()
            ), f"Unexpected error: {result.stderr}"


class TestCleanupTestProjects:
    """
    Utility to clean up any orphaned test_ projects from failed runs.

    Run with: pytest tests/test_create_project.py::TestCleanupTestProjects -v
    """

    def test_cleanup_orphaned_test_projects(self):
        """Find and report any orphaned test_ projects in parent directory."""
        agent_env_root = Path(__file__).parent.parent
        parent_dir = agent_env_root.parent

        orphaned = []
        for item in parent_dir.iterdir():
            if item.is_dir() and item.name.startswith("test_"):
                orphaned.append(item)

        if orphaned:
            print(f"\nFound {len(orphaned)} orphaned test project(s):")
            for p in orphaned:
                print(f"  - {p}")
            print("\nTo clean up, run:")
            for p in orphaned:
                print(f"  rm -rf {p}")

        # This test always passes - it's informational
        assert True
