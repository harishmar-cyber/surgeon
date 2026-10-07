import os
import re


def extract_suspect_files(pytest_output):
    """Find Python files mentioned in stack traces."""
    files = []
    pattern = r'([a-zA-Z0-9_\-/]+\.py):\d+'
    for match in re.finditer(pattern, pytest_output):
        f = match.group(1)
        basename = os.path.basename(f)
        if basename.startswith("test_"):
            continue
        if "site-packages" in f or "venv" in f:
            continue
        if f not in files:
            files.append(f)
    return files


def extract_source_context(repo_path, file_path, max_lines=150):
    """Read the suspect file."""
    full = os.path.join(repo_path, file_path)
    if not os.path.exists(full):
        for root, _, filenames in os.walk(repo_path):
            if os.path.basename(file_path) in filenames:
                full = os.path.join(root, os.path.basename(file_path))
                break

    if not os.path.exists(full):
        return None

    with open(full, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    return "".join(lines[:max_lines])