"""Create a `wildfire_ml` folder next to this script and clone (or update) the
wildfire-ml GitHub repository into it.

Usage (from the repository root):

    python setup_wildfire_ml.py

First run:  clones https://github.com/greenj63/wildfire-ml into ./wildfire_ml
Later runs: fast-forwards ./wildfire_ml to the latest commit on its current branch.

Requires git on PATH. Uses only the Python standard library.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

REPO_URL = "https://github.com/greenj63/wildfire-ml.git"
FOLDER_NAME = "wildfire_ml"

# The folder is created in the same directory as this script (the repository root).
TARGET = Path(__file__).resolve().parent / FOLDER_NAME


def run_git(args: list[str], cwd: Path | None = None) -> None:
    """Run a git command, streaming its output, and exit on failure."""
    cmd = ["git", *args]
    print(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        sys.exit(f"error: command failed with exit code {result.returncode}")


def main() -> None:
    if shutil.which("git") is None:
        sys.exit(
            "error: git was not found on PATH. Install Git for Windows and try again."
        )

    if not TARGET.exists():
        TARGET.mkdir()
        print(f"Created folder: {TARGET}")
        run_git(["clone", REPO_URL, str(TARGET)])
        print("Clone complete.")
        return

    if not (TARGET / ".git").exists():
        sys.exit(
            f"error: {TARGET} already exists but is not a git repository.\n"
            f"Move or delete it, then run this script again."
        )

    print(f"Folder already exists: {TARGET}")
    run_git(["pull", "--ff-only"], cwd=TARGET)
    print("Update complete.")


if __name__ == "__main__":
    main()
