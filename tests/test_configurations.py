#!/usr/bin/env python3
import json
import os
import subprocess
from pathlib import Path


def run_command(cmd, cwd=None):
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error Code: {result.returncode}")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
    return result


def get_dir_size(path):
    total = 0
    if not os.path.exists(path):
        return 0
    for p in Path(path).rglob("*"):
        if p.is_file() and not p.is_symlink():
            try:
                total += p.stat().st_size
            except FileNotFoundError:
                pass
    return total


def format_size(size_bytes):
    if size_bytes == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB")
    import math

    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"


def main():
    root_dir = Path(__file__).resolve().parent.parent
    results_file = root_dir / "logs" / "config_test_results.json"

    configs = [
        {
            "name": "Minimal (Python Only)",
            "enable_lang": ["python"],
            "disable_lang": ["typescript"],
            "disable_feature": ["documentation"],
        },
        {
            "name": "Web/TypeScript",
            "enable_lang": ["typescript"],
            "disable_lang": ["python"],
            "disable_feature": ["documentation"],
        },
        {
            "name": "Full (All features)",
            "enable_lang": ["python", "typescript"],
            "enable_feature": ["documentation"],
        },
    ]

    report = []

    # One-time stash
    print("Stashing local changes...")
    has_changes = subprocess.run(
        ["git", "status", "-s"], capture_output=True, text=True
    ).stdout.strip()
    stashed = False
    if has_changes:
        run_command(
            [
                "git",
                "stash",
                "push",
                "--include-untracked",
                "-m",
                "Temp stash for config tests",
            ],
            cwd=root_dir,
        )
        stashed = True

    try:
        for cfg in configs:
            print(f"\n--- Testing Configuration: {cfg['name']} ---")

            # 1. Reset pristine (force local for speed)
            run_command(["bash", "bin/reset_pristine.sh", "--yes", "--force"], cwd=root_dir)

            # 2. Configure
            configure_cmd = ["python3", "bin/configure.py", "--non-interactive"]
            for lang in cfg.get("enable_lang", []):
                configure_cmd += ["--enable-lang", lang]
            for lang in cfg.get("disable_lang", []):
                configure_cmd += ["--disable-lang", lang]
            for feat in cfg.get("enable_feature", []):
                configure_cmd += ["--enable-feature", feat]
            for feat in cfg.get("disable_feature", []):
                configure_cmd += ["--disable-feature", feat]

            run_command(configure_cmd, cwd=root_dir)

            # 3. Env Sync
            run_command(["bash", "bin/ensure_env.sh"], cwd=root_dir)

            # 4. Measure and Verify Side Effects
            venv_path = root_dir / ".venv"
            node_modules_path = root_dir / "node_modules"

            python_enabled = "python" in cfg.get("enable_lang", []) or (
                "python" not in cfg.get("disable_lang", []) and cfg["name"] == "Full (All features)"
            )
            ts_enabled = "typescript" in cfg.get("enable_lang", []) or (
                "typescript" not in cfg.get("disable_lang", [])
                and cfg["name"] == "Full (All features)"
            )

            # Validate physical state
            if python_enabled and not venv_path.exists():
                print("FAILED: .venv missing but python enabled")
            if not ts_enabled and node_modules_path.exists():
                print("FAILED: node_modules exists but typescript disabled")

            # 5. Validate (skip E2E for speed)
            validation_result = run_command(["bash", "bin/validate.sh", "--fast"], cwd=root_dir)

            # 6. Check Validation Log for skipped components
            log_file = root_dir / "logs" / "validation_summary_log.md"
            log_content = log_file.read_text() if log_file.exists() else ""

            skipped_correctly = True
            if not ts_enabled and "JavaScript disabled in config. Skipping" not in log_content:
                print("FAILED: Validation log does not mention skipping JS")
                skipped_correctly = False

            # 7. Measure Disk Usage
            venv_size = get_dir_size(venv_path)
            node_modules_size = get_dir_size(node_modules_path)
            total_size = get_dir_size(root_dir)

            status = "PASS"
            if validation_result.returncode != 0:
                status = "FAIL (Exit Code)"
            elif not skipped_correctly:
                status = "FAIL (Skip Logic)"
            # Note: We DON'T check for .venv absence because core scripts NEED it.
            if not ts_enabled and node_modules_path.exists():
                status = "FAIL (Node State)"

            report.append(
                {
                    "config": cfg["name"],
                    "status": status,
                    "total_size": format_size(total_size),
                    "venv_size": format_size(venv_size),
                    "node_modules_size": format_size(node_modules_size),
                }
            )

    finally:
        if stashed:
            print("\nRestoring local changes...")
            run_command(["git", "stash", "pop"], cwd=root_dir)

    # Save report
    os.makedirs(root_dir / "logs", exist_ok=True)
    with open(results_file, "w") as f:
        json.dump(report, f, indent=2)

    print("\n--- Configuration Test Summary ---")
    print(f"| {'Config':<20} | {'Status':<6} | {'Total':<10} | {'Venv':<10} | {'Node':<10} |")
    print("|" + "-" * 22 + "|" + "-" * 8 + "|" + "-" * 12 + "|" + "-" * 12 + "|" + "-" * 12 + "|")
    for r in report:
        print(
            f"| {r['config']:<20} | {r['status']:<6} | {r['total_size']:<10} | "
            f"{r['venv_size']:<10} | {r['node_modules_size']:<10} |"
        )


if __name__ == "__main__":
    main()
