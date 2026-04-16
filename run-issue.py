#!/usr/bin/env python3
"""运行 issue 的特征提取。

用法:
    python3 run-issue.py verilator-6988 [--force]        # 单 issue (manager agent)
    python3 run-issue.py --batch id1 id2 id3 ...          # 批量 (batch-manager agent)
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


def run_single(issue_id: str, force: bool = False):
    """运行单个 issue 的特征提取 (manager agent)。"""
    issue_id = issue_id.strip("/").replace("issues/", "")
    issue_dir = ROOT / "issues" / issue_id
    if not issue_dir.is_dir():
        print(f"Issue dir not found: {issue_dir}", file=sys.stderr)
        sys.exit(1)

    input_path = issue_dir / "issue_input.json"
    if not input_path.exists():
        print(f"No issue_input.json in {issue_dir}", file=sys.stderr)
        sys.exit(1)

    output = issue_dir / "output" / "features.json"
    if output.is_file() and not force:
        print(f"Already done: {issue_id}")
        return

    (issue_dir / "output").mkdir(exist_ok=True)
    (issue_dir / "workspace").mkdir(exist_ok=True)

    # 读取 issue 信息
    issue_info = json.loads(input_path.read_text())
    issue_rel = f"issues/{issue_id}"

    # 构造 prompt
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

    config = load_config()
    env = os.environ.copy()
    env["SUBAGENT_PARALLELISM"] = str(config.get("subagent_parallelism", 2))

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


def run_batch(issue_ids: list[str]):
    """批量处理多个 issue (batch-manager agent)。"""
    # 确保所有 issue 目录和输出目录存在
    valid_ids = []
    for issue_id in issue_ids:
        issue_dir = ROOT / "issues" / issue_id
        if not issue_dir.is_dir():
            print(f"Warning: skipping {issue_id} (dir not found)", file=sys.stderr)
            continue
        output = issue_dir / "output" / "features.json"
        if output.is_file():
            continue  # 已完成
        (issue_dir / "output").mkdir(exist_ok=True)
        (issue_dir / "workspace").mkdir(exist_ok=True)
        valid_ids.append(issue_id)

    if not valid_ids:
        print("All issues in batch already done.")
        return

    prompt = (
        f"Process {len(valid_ids)} issues. "
        f"Issue IDs: {' '.join(valid_ids)}. "
        f"For each issue: dispatch an extractor sub-agent to read "
        f"issues/{{id}}/issue_input.json and write output to "
        f"issues/{{id}}/output/features.json. "
        f"Dispatch 2 sub-agents at a time using run_in_background. "
        f"Wait for both to complete before dispatching the next pair."
    )

    config = load_config()
    env = os.environ.copy()
    timeout = max(len(valid_ids) * 120, 600)  # 至少 10 min, 每 issue 2 min

    log_dir = ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    session_log = log_dir / f"session-batch-{valid_ids[0]}-to-{valid_ids[-1]}.jsonl"

    cmd = [
        "claude", "-p",
        "--verbose",
        "--output-format", "stream-json",
        "--agent", "batch-manager",
        prompt,
    ]

    start = time.time()
    print(f"Batch: {len(valid_ids)} issues, timeout={timeout}s")
    try:
        with open(session_log, "w") as f:
            subprocess.run(cmd, stdout=f, timeout=timeout,
                           check=False, cwd=str(ROOT), env=env)
    except subprocess.TimeoutExpired:
        print(f"Batch timeout after {timeout}s", file=sys.stderr)

    dur = time.time() - start

    # 统计结果
    done = 0
    failed = 0
    for issue_id in valid_ids:
        output = ROOT / "issues" / issue_id / "output" / "features.json"
        if output.is_file():
            done += 1
        else:
            failed += 1

    print(f"Batch done: {done}/{len(valid_ids)} succeeded, "
          f"{failed} failed ({dur:.0f}s)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("issue_id", nargs="?",
                        help="e.g. verilator-6988 or issues/verilator-6988/")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--batch", nargs="+",
                        help="Batch mode: process multiple issue IDs")
    args = parser.parse_args()

    if args.batch:
        run_batch(args.batch)
    elif args.issue_id:
        run_single(args.issue_id, args.force)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
