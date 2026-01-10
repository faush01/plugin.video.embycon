#!/usr/bin/env python3
"""
Parse Kodi log file and extract EmbyCon timing data to JSON.

Usage:
    python parse_timing_log.py [input_log_file] [output_json_file]

If no arguments provided, defaults to:
    - Input: kodi.log (in current directory)
    - Output: timing_data.json
"""

from __future__ import annotations

import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def parse_timing_line(line: str) -> dict[str, Any] | None:
    """
    Parse a timing log line and extract relevant data.

    Expected format:
    YYYY-MM-DD HH:MM:SS.mmm T:<thread_id> info <general>: EmbyCon.resources.lib.tracking|INFO|timing_data|<function>|<start>|<end>|

    Returns:
        dict or None: Parsed data with keys: id, function, start, end
    """
    # Check if line contains timing_data
    if "EmbyCon.resources.lib.tracking|INFO|timing_data|" not in line:
        return None

    # Extract thread ID
    thread_match = re.search(r"T:(\d+)", line)
    if not thread_match:
        return None

    thread_id = int(thread_match.group(1))

    # Extract the tracking data part (after the colon)
    parts = line.split(":", 3)  # Split on first 3 colons to get the message part
    if len(parts) < 4:
        return None

    message_part = parts[3].strip()

    # Split by pipe to get tracking fields
    # Expected: EmbyCon.resources.lib.tracking|INFO|timing_data|<function>|<start>|<end>|
    fields = message_part.split("|")

    # We need at least 6 fields
    if len(fields) < 6 or fields[2] != "timing_data":
        return None

    try:
        function_name = fields[3]
        start_time = float(fields[4])
        end_time = float(fields[5])

        # Extract data field (field 6 or beyond)
        # Join all remaining fields in case the data contains pipes
        data = ""
        if len(fields) > 6:
            data = "|".join(fields[6:]).strip()

        return {
            "id": thread_id,
            "function": function_name,
            "start": start_time,
            "end": end_time,
            "data": data,
        }
    except (ValueError, IndexError):
        return None


def parse_log_file(log_file_path: str, output_file_path: str) -> None:
    """
    Parse the log file and extract all timing data entries.

    Args:
        log_file_path (str): Path to the Kodi log file
        output_file_path (str): Path to the output JSON file
    """
    log_path = Path(log_file_path)

    if not log_path.exists():
        logger.error("Log file not found: %s", log_file_path)
        sys.exit(1)

    timing_entries = []

    logger.info("Parsing log file: %s", log_file_path)

    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        for _line_num, line in enumerate(f, 1):
            parsed = parse_timing_line(line)
            if parsed:
                timing_entries.append(parsed)

    logger.info("Found %d timing entries", len(timing_entries))

    # Write to JSON file
    output_path = Path(output_file_path)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(timing_entries, f, indent=2)

    logger.info("Timing data saved to: %s", output_file_path)


def main() -> None:
    """Main entry point."""
    # Configure logger
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    # Default file paths
    default_input = "kodi.log"
    default_output = "timing_data.json"

    # Get file paths from command line or use defaults
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = default_input

    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    else:
        output_file = default_output

    parse_log_file(input_file, output_file)


if __name__ == "__main__":
    main()
