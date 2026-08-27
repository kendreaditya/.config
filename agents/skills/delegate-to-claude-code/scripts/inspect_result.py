#!/usr/bin/env python3
"""Print a compact, non-secret summary of a run_claude.py result."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path)
    ns = parser.parse_args()
    data = json.loads(ns.result.read_text(encoding="utf-8"))
    keys = (
        "schema", "status", "exitCode", "processExitCode", "signal", "workdir", "outDir", "claudeVersion",
        "requestedModel", "effectiveModel", "requestedEffort", "permissionMode",
        "dangerouslySkipPermissions", "sessionId", "resultSubtype", "isError",
        "numTurns", "totalCostUsd", "gitStatusBefore", "gitStatusAfter",
        "startedAt", "finishedAt", "events", "stderr", "final", "result",
    )
    summary = {key: data.get(key) for key in keys if key in data}
    final_message = data.get("finalMessage")
    if isinstance(final_message, str):
        summary["finalMessagePreview"] = final_message[:1000]
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
