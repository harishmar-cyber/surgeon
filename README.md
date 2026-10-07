# SURGEON: Test-Driven Code Repair Agent

An AI agent that fixes bugs in Python code by generating minimal fixes and verifying them via the test suite.

## What It Does

1. Runs the baseline test suite to find failing tests
2. Localizes the bug via stack trace analysis
3. Uses an LLM (Groq / OpenAI) to generate a fix
4. Writes the fix to a sandboxed copy of the repo
5. Re-runs the FULL test suite to verify
6. Detects regressions — if anything else breaks, the fix is rejected

## Why It's Different

- **Regression guard** — verifies nothing else broke
- **Sandboxed execution** — original repo is never touched
- **Proof package** — every fix comes with before/after test results
- **Simple, deterministic** — no complex patch formats, no LLM guessing

## Architecture
