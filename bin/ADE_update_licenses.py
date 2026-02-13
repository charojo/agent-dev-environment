#!/usr/bin/env python3
# ## @DOC
# ### Ade Update Licenses
# Updates license information in source files.


"""
ADE_update_licenses.py

Consolidated script to:
1. Generate frontend licenses (via npx license-checker)
2. Generate backend licenses (via pip-licenses)
3. Merge them into a unified format for the application
"""

import datetime
import json
import shutil
import subprocess
import sys
from pathlib import Path

def log(msg):
    """Print message with timestamp."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")


# Paths
# This script is in agent_env/bin/
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
SRC_WEB_DIR = PROJECT_ROOT / "src" / "web"
LICENSES_DIR = PROJECT_ROOT / "licenses"
FRONTEND_LICENSES_FILE = LICENSES_DIR / "frontend-licenses.json"
BACKEND_LICENSES_FILE = LICENSES_DIR / "backend-licenses.json"
# Fallback output location if src/web is missing
OUTPUT_FILE = SRC_WEB_DIR / "src" / "features" / "settings" / "licenses.json"
if not SRC_WEB_DIR.exists():
    OUTPUT_FILE = PROJECT_ROOT / "licenses.json"


def run_command(cmd, cwd=None, capture_output=True):
    """Run a shell command and return result."""
    log(f"Running command: {' '.join(cmd)}")
    if cwd:
        log(f"  CWD: {cwd}")
    
    try:
        if capture_output:
            result = subprocess.run(
                cmd, cwd=cwd, capture_output=True, text=True, check=True
            )
            return result
        else:
            # Stream output directly to stdout/stderr
            result = subprocess.run(
                cmd, cwd=cwd, text=True, check=True
            )
            return result
    except subprocess.CalledProcessError as e:
        log(f"Error running command: {' '.join(cmd)}")
        if hasattr(e, 'stderr') and e.stderr:
            print(f"Stderr: {e.stderr}")
        raise



def generate_frontend_licenses():
    """Run license-checker to generate frontend licenses."""
    if not SRC_WEB_DIR.exists():
        log("No frontend (src/web) found. Skipping frontend licenses.")
        return True
    # Check for package.json
    if not (SRC_WEB_DIR / "package.json").exists():
        log("No package.json found in src/web. Skipping frontend licenses.")
        return True

    log("Generating Frontend Licenses...")

    # Ensure licenses dir exists
    LICENSES_DIR.mkdir(exist_ok=True)
    log(f"Licenses directory: {LICENSES_DIR}")


    cmd = [
        "npx",
        "-y",
        "license-checker",
        "--json",
        "--out",
        str(FRONTEND_LICENSES_FILE),
        "--production",
        "--excludePrivatePackages",
    ]

    # Check if npx is available
    if not shutil.which("npx"):
        print("Error: npx not found. Ensure Node.js is installed.")
        return False

    try:
        # For frontend, we want to see what's happening if it hangs
        run_command(cmd, cwd=SRC_WEB_DIR, capture_output=False)
        log("✓ Frontend licenses generated.")
        return True
    except subprocess.CalledProcessError:
        log("Failed to generate frontend licenses.")
        return False



def generate_backend_licenses():
    """Run pip-licenses to generate backend licenses."""
    log("Generating Backend Licenses...")


    # Determine pip-licenses command
    venv_pip_licenses = PROJECT_ROOT / ".venv" / "bin" / "pip-licenses"
    pip_licenses_cmd = "pip-licenses"

    if venv_pip_licenses.exists():
        pip_licenses_cmd = str(venv_pip_licenses)

    # Fallback to uv tool run if pip-licenses is missing
    if pip_licenses_cmd == "pip-licenses" and not shutil.which("pip-licenses"):
        if shutil.which("uv"):
            pip_licenses_cmd = "uv"

    # Prepare command args
    cmd_args = [pip_licenses_cmd]
    if pip_licenses_cmd == "uv":
        cmd_args = ["uv", "run", "--with", "pip-licenses", "pip-licenses"]

    cmd_args.extend(["--format=json", "--with-urls", "--with-authors"])

    try:
        result = run_command(cmd_args, cwd=PROJECT_ROOT)
        licenses_data = json.loads(result.stdout)

        # Transform to match frontend format
        transformed = {}
        for pkg in licenses_data:
            name = pkg.get("Name", "unknown")
            version = pkg.get("Version", "0.0.0")
            license_type = pkg.get("License", "UNKNOWN")
            url = pkg.get("URL", "")
            author = pkg.get("Author", "")

            # Create key in format: name@version
            key = f"{name}@{version}"

            entry = {
                "licenses": license_type,
                "repository": url,
                "publisher": author,
                "source": "backend",
            }

            if not url:
                entry.pop("repository", None)
            if not author:
                entry.pop("publisher", None)

            transformed[key] = entry

        # Write to intermediate file
        log(f"Writing backend licenses to {BACKEND_LICENSES_FILE}")
        with open(BACKEND_LICENSES_FILE, "w", encoding="utf-8") as f:
            json.dump(transformed, f, indent=2, ensure_ascii=False)

        log(f"✓ Generated {len(transformed)} Python package licenses")
        return True


    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        print(f"Error generating backend licenses: {e}")
        return False


def make_path_relative(abs_path):
    """Convert absolute path to relative path from project root."""
    if not abs_path:
        return abs_path

    try:
        path_obj = Path(abs_path)
        if path_obj.is_absolute():
            return str(path_obj.relative_to(PROJECT_ROOT))
    except ValueError:
        pass

    return abs_path


def merge_licenses():
    """Merge frontend and backend licenses into final output."""
    print("Merging Licenses...")

    try:
        frontend_processed = {}
        if FRONTEND_LICENSES_FILE.exists():
            with open(FRONTEND_LICENSES_FILE, "r", encoding="utf-8") as f:
                frontend_data = json.load(f)

            # Process frontend licenses (add source, fix paths)
            for key, value in frontend_data.items():
                new_val = value.copy()
                new_val["source"] = "frontend"
                if "path" in new_val:
                    new_val["path"] = make_path_relative(new_val["path"])
                if "licenseFile" in new_val:
                    new_val["licenseFile"] = make_path_relative(new_val["licenseFile"])
                frontend_processed[key] = new_val

        if BACKEND_LICENSES_FILE.exists():
            with open(BACKEND_LICENSES_FILE, "r", encoding="utf-8") as f:
                backend_data = json.load(f)
        else:
            print(f"Error: {BACKEND_LICENSES_FILE} not found.")
            return False

        # Merge
        merged = {**frontend_processed, **backend_data}

        # Ensure output dir exists
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2, ensure_ascii=False)

        print(
            f"✓ Merged {len(frontend_processed)} frontend + "
            f"{len(backend_data)} backend = {len(merged)} total licenses"
        )
        print(f"✓ Output written to: {OUTPUT_FILE}")
        return True

    except Exception as e:
        print(f"Error merging licenses: {e}")
        return False


def main():
    log("========================================")
    log("Updating Open Source License Information")
    log("========================================")
    log(f"Project Root: {PROJECT_ROOT}")

    if not generate_frontend_licenses():
        log("Frontend license generation failed.")
        sys.exit(1)

    if not generate_backend_licenses():
        log("Backend license generation failed.")
        sys.exit(1)

    if not merge_licenses():
        log("Merging licenses failed.")
        sys.exit(1)

    # Cleanup intermediate files
    log("Cleaning up intermediate files...")
    for f in [FRONTEND_LICENSES_FILE, BACKEND_LICENSES_FILE]:
        if f.exists():
            log(f"Removing {f}")
            f.unlink()
    if LICENSES_DIR.exists() and not any(LICENSES_DIR.iterdir()):
        log(f"Removing empty {LICENSES_DIR}")
        LICENSES_DIR.rmdir()

    log("========================================")
    log("Success! License information updated.")
    log("========================================")



if __name__ == "__main__":
    main()
