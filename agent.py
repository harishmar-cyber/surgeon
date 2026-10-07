import sys
import os
import tempfile
import shutil
from sandbox import run_tests
from localizer import extract_suspect_files, extract_source_context
from patcher import generate_fixed_file


def print_separator(title=""):
    print("\n" + "=" * 60)
    if title:
        print(f"  {title}")
        print("=" * 60)


def fix_bug(repo_path, failing_test_name):
    print_separator("STEP 1: BASELINE TEST RUN")
    baseline = run_tests(repo_path)
    print(f"  Passed: {len(baseline['passed'])}")
    print(f"  Failed: {len(baseline['failed'])}")
    print(f"  Failing: {baseline['failed']}")

    if not baseline['failed']:
        print("\n  No failing tests. Nothing to fix.")
        return {"success": False, "reason": "no_failures"}

    target = failing_test_name or baseline['failed'][0]
    print(f"\n  Target test: {target}")

    print_separator("STEP 2: CAPTURE FAILURE DETAILS")
    fail_result = run_tests(repo_path, target)
    print(f"  Running target test...")

    print_separator("STEP 3: LOCALIZE BUG")
    suspects = extract_suspect_files(fail_result['stdout'])
    if not suspects:
        for root, _, files in os.walk(repo_path):
            for f in files:
                if f.endswith(".py") and not f.startswith("test_"):
                    suspects.append(os.path.relpath(os.path.join(root, f), repo_path))

    if not suspects:
        return {"success": False, "reason": "no_suspect_files"}

    file_path = suspects[0]
    print(f"  Suspect file: {file_path}")

    source_code = extract_source_context(repo_path, file_path)
    if not source_code:
        return {"success": False, "reason": f"could_not_read_{file_path}"}
    print(f"  Source loaded: {len(source_code)} chars")

    print_separator("STEP 4: GENERATE FIXED FILE")
    print("  Calling LLM...")
    fixed_content = generate_fixed_file(fail_result['stdout'], file_path, source_code)

    if fixed_content.startswith("CANNOT_FIX"):
        print(f"  LLM refused: {fixed_content[:200]}")
        return {"success": False, "reason": "llm_refused"}

    print(f"  Fixed file received ({len(fixed_content)} chars)")
    print("  " + "-" * 56)
    for line in fixed_content.split("\n"):
        print(f"  {line}")
    print("  " + "-" * 56)

    print_separator("STEP 5: WRITE FIXED FILE TO SANDBOX")
    tmp = tempfile.mkdtemp(prefix="surgeon_")
    patched_path = os.path.join(tmp, "repo")
    shutil.copytree(repo_path, patched_path)

    target_file = os.path.join(patched_path, file_path)
    # Normalize line endings to match Linux style (avoid git issues)
    fixed_content_clean = fixed_content.replace("\r\n", "\n")
    with open(target_file, "w", encoding="utf-8", newline="\n") as f:
        f.write(fixed_content_clean)

    print(f"  Wrote fixed content to: {target_file}")

    print_separator("STEP 6: VERIFY (RUN FULL SUITE)")
    after = run_tests(patched_path)
    print(f"  Passed: {len(after['passed'])}")
    print(f"  Failed: {len(after['failed'])}")

    new_failures = set(after['failed']) - set(baseline['failed'])
    target_fixed = len(after['failed']) < len(baseline['failed'])

    print_separator("STEP 7: RESULTS")
    print(f"  Target test fixed: {target_fixed}")
    print(f"  New regressions: {list(new_failures)}")

    success = target_fixed and len(new_failures) == 0
    print(f"\n  >>> OVERALL: {'SUCCESS' if success else 'FAILED'}")

    return {
        "success": success,
        "file": file_path,
        "target_fixed": target_fixed,
        "regressions": list(new_failures),
    }


if __name__ == "__main__":
    repo = sys.argv[1] if len(sys.argv) > 1 else "tiny_repo"
    test_name = sys.argv[2] if len(sys.argv) > 2 else None
    print(f"Repo: {repo}")
    print(f"Test: {test_name or '(auto-detect)'}")
    result = fix_bug(repo, test_name)
    print("\n" + "=" * 60)
    if result.get("success"):
        print("FINAL: SUCCESS")
    else:
        print(f"FINAL: FAILED - {result.get('reason', 'unknown')}")