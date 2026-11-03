import fnmatch
import subprocess
import sys

import yaml


def changed_files():
    out = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        capture_output=True, text=True, check=True,
    ).stdout
    return [line[3:].strip() for line in out.splitlines() if line.strip()]


def check(files, protected):
    problems = []
    if not files:
        problems.append("agent made no changes")
    for f in files:
        if any(fnmatch.fnmatch(f, p) for p in protected):
            problems.append(f"protected file changed: {f}")
    if files and not any(f.startswith("tests/") for f in files):
        problems.append("no test file added or changed")
    return problems


if __name__ == "__main__":
    with open(".selfheal/config.yml") as fh:
        protected = yaml.safe_load(fh).get("protected_files", [])
    problems = check(changed_files(), protected)
    for p in problems:
        print(f"::error::{p}")
    sys.exit(1 if problems else 0)
