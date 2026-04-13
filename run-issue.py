#!/usr/bin/env python3
"""运行单个 issue 的特征提取 (调用 manager agent).

用法:
    python3 run-issue.py verilator-6988 [--force]
    python3 run-issue.py issues/verilator-6988/ [--force]
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load_config() -> dict:
    cfg_path = ROOT / "config.yaml"
    if cfg_path.exists():
        import yaml
        return yaml.safe_load(cfg_path.read_text()) or {}
    return {}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("issue_id", help="e.g. verilator-6988 or issues/verilator-6988/")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    # 规范化路径
    issue_id = args.issue_id.strip("/").replace("issues/", "")
    issue_dir = ROOT / "issues" / issue_id
    if not issue_dir.is_dir():
        print(f"Issue dir not found: {issue_dir}", file=sys.stderr)
        sys.exit(1)

    input_path = issue_dir / "issue_input.json"
    if not input_path.exists():
        print(f"No issue_input.json in {issue_dir}", file=sys.stderr)
        sys.exit(1)

    output = issue_dir / "output" / "features.json"
    if output.is_file() and not args.force:
        print(f"Already done: {issue_id}")
        return

    (issue_dir / "output").mkdir(exist_ok=True)
    (issue_dir / "workspace").mkdir(exist_ok=True)

    # 读取 issue 信息
    issue_info = json.loads(input_path.read_text())
    issue_rel = f"issues/{issue_id}"

    # 构造 prompt
    code_blocks_info = ""
    code_blocks = issue_info.get("code_blocks", [])
    if code_blocks:
        code_blocks_info = f"Found {len(code_blocks)} code blocks in the issue body. "
    else:
        code_blocks_info = "No code blocks found — extract from title and description text. "

    prompt = (
        f"Process {issue_info['tool']} {issue_info['type']} #{issue_info['issue_number']} "
        f"\"{issue_info['title']}\". "
        f"Issue working directory: {issue_rel}/ "
        f"Read {issue_rel}/issue_input.json for full details. "
        f"{code_blocks_info}"
        f"Follow the ExtractLLM three-step method: "
        f"1) Read & understand the bug report, "
        f"2) Synthesize to identify critical SV constructs, "
        f"3) Dispatch extractor(s) to abstract features. "
        f"Write intermediate files to {issue_rel}/workspace/ "
        f"and final output to {issue_rel}/output/features.json. "
        f"IMPORTANT: Use Write tool (not Bash) for all JSON output. "
        f"All features must include: name, category, description, snippet, tags, "
        f"source_bug_id, tool, issue_url, construct_complexity, ub_type."
    )

    # 环境变量
    config = load_config()
    env = os.environ.copy()
    env["SUBAGENT_PARALLELISM"] = str(config.get("subagent_parallelism", 2))

    # 日志
    log_dir = ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    session_log = log_dir / f"session-{issue_id}.jsonl"

    cmd = [
        "claude", "-p",
        "--verbose",
        "--output-format", "stream-json",
        "--agent", "manager",
        prompt,
    ]

    start = time.time()
    try:
        with open(session_log, "w") as f:
            subprocess.run(cmd, stdout=f, timeout=config.get("timeout", 600),
                           check=False, cwd=str(ROOT), env=env)
    except subprocess.TimeoutExpired:
        print(f"Timeout: {issue_id}", file=sys.stderr)
        sys.exit(1)

    dur = time.time() - start

    if output.is_file():
        data = json.loads(output.read_text())
        n = len(data.get("features", []))
        skipped = data.get("skipped_reason")
        if skipped:
            print(f"Skipped: {issue_id} ({skipped}, {dur:.0f}s)")
        else:
            print(f"Done: {issue_id} ({n} features, {dur:.0f}s)")
    else:
        print(f"Failed: {issue_id} (no output after {dur:.0f}s)", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
