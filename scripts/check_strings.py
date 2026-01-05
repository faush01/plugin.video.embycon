#!/usr/bin/env python3
"""
Check for unused string IDs in the English language strings.po file.
Python version of check_strings.ps1
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def get_repo_root() -> Path:
    """Get the git repository root directory."""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(result.stdout.strip())


def find_string_ids(strings_po_path: Path) -> list[tuple[str, str]]:
    """Extract all string IDs and their text from the strings.po file."""
    string_data = []
    seen_ids = set()

    with open(strings_po_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("msgctxt "):
            match = re.search(r'"#(\d+)"', line)
            if match:
                string_id = match.group(1)
                if string_id in seen_ids:
                    raise Exception(f"ERROR: String ID Already Exists : {string_id}")

                seen_ids.add(string_id)
                # Look for the msgid on the next line
                if i + 1 < len(lines) and lines[i + 1].startswith("msgid "):
                    msgid_match = re.search(r'"(.*)"', lines[i + 1])
                    if msgid_match:
                        string_text = msgid_match.group(1)
                        string_data.append((string_id, string_text))
        i += 1

    return string_data


def find_files_with_pattern(repo_root: Path, patterns: list[str]) -> list[Path]:
    """Find all files matching the given patterns."""
    files = []
    for pattern in patterns:
        files.extend(repo_root.rglob(pattern))
    return files


def search_string_usage(string_id: str, search_files: list[Path]) -> int:
    """Search for string ID usage in all relevant files and return count."""
    count = 0
    for file_path in search_files:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                if string_id in content:
                    count += 1
        except Exception:
            # Skip files that can't be read
            pass
    return count


def find_string_load_references(repo_root: Path) -> set[str]:
    """Find all string_load() calls in Python files and extract the string IDs."""
    string_ids = set()
    pattern = re.compile(r"string_load\s*\(\s*(\d+)\s*\)")

    # Find all Python files
    python_files = list(repo_root.rglob("*.py"))

    for py_file in python_files:
        try:
            with open(py_file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                matches = pattern.findall(content)
                for match in matches:
                    string_ids.add(match)
        except Exception:
            # Skip files that can't be read
            pass

    return string_ids


def main() -> None:
    # Get repository root
    repo_root = get_repo_root()

    # Path to the English strings.po file
    strings_po: Path = Path(
        os.path.join(
            repo_root,
            "plugin.video.embycon",
            "resources",
            "language",
            "resource.language.en_gb",
            "strings.po",
        )
    )

    if not strings_po.exists():
        logger.error("strings.po not found at %s", strings_po)
        return

    # Get all string IDs
    logger.info("Extracting string IDs from strings.po...")
    string_data = find_string_ids(strings_po)
    defined_string_ids = {string_id for string_id, _ in string_data}

    # Get all files to search
    logger.info("Finding files to search...")
    search_files = []
    search_files.extend(repo_root.rglob("*.py"))
    search_files.append(
        Path(
            os.path.join(repo_root, "plugin.video.embycon", "resources", "settings.xml")
        )
    )
    search_files.append(strings_po)

    # Check usage of each string ID
    logger.info("Checking string usage...\n")
    logger.info("=== Unused Strings ===")
    for string_id, string_text in string_data:
        usage_count = search_string_usage(string_id, search_files)
        if usage_count == 1:
            # Only found in strings.po itself (unused)
            logger.info(
                "ID: %s\tCount: %s\tText: '%s', ", string_id, usage_count, string_text
            )

    # Find all string_load() references and check if they exist
    logger.info("\n=== Checking string_load() References ===")
    referenced_ids = find_string_load_references(repo_root)

    missing_ids = referenced_ids - defined_string_ids

    if missing_ids:
        logger.info("\nMissing string IDs (referenced but not defined):")
        for missing_id in sorted(missing_ids, key=int):
            logger.info("  Missing ID: %s", missing_id)
    else:
        logger.info("\nAll string_load() references are valid!")

    logger.info("\nSummary:")
    logger.info("  Total strings defined: %d", len(defined_string_ids))
    logger.info("  Total string_load() references found: %d", len(referenced_ids))
    logger.info("  Missing string definitions: %d", len(missing_ids))


if __name__ == "__main__":
    main()
