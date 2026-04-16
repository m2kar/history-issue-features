#!/usr/bin/env python3
"""SubagentStop hook: log agent completion to logs/progress.log."""
import json
import os
import sys
from datetime import datetime, timezone

try:
    event = json.load(sys.stdin)
except Exception:
    sys.exit(0)

agent = event.get("agent_name") or event.get("subagent_name") or "unknown"
status = "done" if not event.get("error") else "error"
ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
line = f"{ts}  {status:6s}  {agent}\n"

# 写到项目根的 logs/progress.log
cwd = os.getcwd()
root = cwd
for _ in range(10):
    if os.path.exists(os.path.join(root, "config.yaml")):
        break
    root = os.path.dirname(root)

log_dir = os.path.join(root, "logs")
os.makedirs(log_dir, exist_ok=True)
with open(os.path.join(log_dir, "progress.log"), "a") as f:
    f.write(line)

print(f"[progress] {line.rstrip()}", file=sys.stderr)
sys.exit(0)
