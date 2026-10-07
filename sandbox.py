import subprocess
import shutil
import tempfile
import os
import re
import sys


def run_tests(repo_path, test_filter=None):
    """Run pytest and return structured results."""
    repo_path = os.path.abspath(repo_path)

    # Use the SAME python that runs this script (venv)
    cmd = [sys.executable, "-m", "pytest", "-v", "--tb=short", "--no-header"]
    if test_filter:
        cmd.append(test_filter)

    try:
        result = subprocess.run(
            cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=120
        )
    except subprocess.TimeoutExpired:
        return {"passed": [], "failed": [], "errors": ["TIMEOUT"], "stdout": "", "returncode": -1}

    passed, failed, errors = [], [], []
    output = result.stdout + "\n" + result.stderr

    for line in output.split("\n"):
        line_stripped = line.strip()
        if " PASSED" in line_stripped:
            parts = line_stripped.split("::")
            if len(parts) > 1:
                name = parts[-1].split(" ")[0].strip()
                passed.append(name)
        elif " FAILED" in line_stripped:
            parts = line_stripped.split("::")
            if len(parts) > 1:
                name = parts[-1].split(" ")[0].strip()
                failed.append(name)
        elif line_stripped.startswith("ERROR"):
            errors.append(line_stripped)

    return {
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "stdout": output,
        "returncode": result.returncode
    }


def apply_diff_to_copy(repo_path, diff_text):
    """Copy repo, apply git diff with multiple fallback strategies."""
    repo_path = os.path.abspath(repo_path)
    tmp = tempfile.mkdtemp(prefix="surgeon_")
    copy_path = os.path.join(tmp, "repo")
    shutil.copytree(repo_path, copy_path)

    # Clean up markdown fences if present
    diff_text = diff_text.strip()
    if diff_text.startswith("```"):
        diff_text = re.sub(r'^```[a-z]*\n', '', diff_text)
        diff_text = re.sub(r'\n```$', '', diff_text)

    # Ensure trailing newline
    if not diff_text.endswith("\n"):
        diff_text += "\n"

    patch_file = os.path.join(tmp, "patch.diff")
    with open(patch_file, "w", encoding="utf-8") as f:
        f.write(diff_text)

    # Try multiple strategies, from strict to permissive
    strategies = [
        # 1. Standard apply
        ["git", "apply", "--verbose", patch_file],
        # 2. Recount lines (don't trust @@ numbers)
        ["git", "apply", "--verbose", "--recount", "--whitespace=nowarn", patch_file],
        # 3. Allow zero context lines
        ["git", "apply", "--verbose", "--recount", "--unidiff-zero", "--whitespace=nowarn", patch_file],
        # 4. 3-way merge
        ["git", "apply", "--verbose", "--3way", patch_file],
        # 5. Reject mode (leaves .rej files)
        ["git", "apply", "--verbose", "--reject", "--whitespace=nowarn", patch_file],
    ]

    last_error = ""
    for i, cmd in enumerate(strategies, 1):
        result = subprocess.run(
            cmd,
            cwd=copy_path,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return copy_path, None
        last_error += f"\n[Strategy {i}: {' '.join(cmd[1:])}]\n{result.stderr}\n"

    return None, last_error


def write_fixed_file(repo_path, file_path, fixed_content):
    """Alternative: directly write fixed file (bypass patch system)."""
    repo_path = os.path.abspath(repo_path)
    tmp = tempfile.mkdtemp(prefix="surgeon_")
    copy_path = os.path.join(tmp, "repo")
    shutil.copytree(repo_path, copy_path)

    target = os.path.join(copy_path, file_path)
    if not os.path.exists(target):
        # Try basename search
        for root, _, files in os.walk(copy_path):
            if os.path.basename(file_path) in files:
                target = os.path.join(root, os.path.basename(file_path))
                break

    with open(target, "w", encoding="utf-8") as f:
        f.write(fixed_content)

    return copy_path, None