#!/usr/bin/env python3
"""按需获取 PR 文件列表和测试文件内容.

用法:
    python3 scripts/fetch_pr_details.py                    # 处理所有已准备的 PR
    python3 scripts/fetch_pr_details.py --repo verilator   # 仅 verilator
    python3 scripts/fetch_pr_details.py --limit 100        # 限制数量

对于每个 type=pull_request 的 issue_input.json:
1. 获取 PR 修改的文件列表
2. 对含 .sv/.v 测试文件的 PR, 获取测试文件内容
3. 更新 issue_input.json 的 pr_files 和 pr_test_files 字段
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ISSUES_DIR = ROOT / "issues"
RAW_DIR = ROOT / "raw"
SLEEP = 1.8  # seconds between API calls

REPOS = {
    "verilator": "verilator/verilator",
    "circt": "llvm/circt",
}


def fetch_pr_files(repo: str, pr_number: int, cache_dir: Path) -> list[dict] | None:
    """获取 PR 修改的文件列表."""
    cache_path = cache_dir / f"{pr_number}.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text())

    env = os.environ.copy()
    env["GH_NO_UPDATE_NOTIFIER"] = "1"
    env["GH_PROMPT_DISABLED"] = "1"

    try:
        result = subprocess.run(
            ["gh", "api", f"/repos/{repo}/pulls/{pr_number}/files",
             "--jq", '[.[] | {filename, status, additions, deletions}]'],
            capture_output=True, text=True, timeout=30, env=env,
        )
    except subprocess.TimeoutExpired:
        return None

    if result.returncode != 0:
        return None

    try:
        files = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None

    cache_path.write_text(json.dumps(files, indent=2) + "\n")
    return files


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", choices=["verilator", "circt"])
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    tools = [args.repo] if args.repo else list(REPOS.keys())
    processed = 0

    for tool in tools:
        repo = REPOS[tool]
        cache_dir = RAW_DIR / f"{tool}_pr_files"
        cache_dir.mkdir(parents=True, exist_ok=True)

        # 找所有 PR 类型的 issue_input.json
        pr_dirs = []
        for issue_dir in sorted(ISSUES_DIR.iterdir()):
            if not issue_dir.name.startswith(f"{tool}-"):
                continue
            input_path = issue_dir / "issue_input.json"
            if not input_path.exists():
                continue
            data = json.loads(input_path.read_text())
            if data.get("type") != "pull_request":
                continue
            if data.get("pr_files") is not None:
                continue  # already fetched
            pr_dirs.append((issue_dir, data))

        print(f"{tool}: {len(pr_dirs)} PRs to fetch")

        for issue_dir, data in pr_dirs:
            if args.limit and processed >= args.limit:
                break

            num = data["issue_number"]
            files = fetch_pr_files(repo, num, cache_dir)
            if files is None:
                print(f"  Failed: {tool}-{num}")
                continue

            # 找 .sv/.v 测试文件
            test_files = [f for f in files
                          if f["filename"].endswith((".sv", ".v"))
                          and ("test" in f["filename"].lower()
                               or "t_" in f["filename"]
                               or f["status"] == "added")]

            data["pr_files"] = [f["filename"] for f in files]
            data["pr_test_files"] = {f["filename"]: None for f in test_files}

            input_path = issue_dir / "issue_input.json"
            input_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
            processed += 1
            print(f"  {tool}-{num}: {len(files)} files, {len(test_files)} test files")
            time.sleep(SLEEP)

    print(f"\nProcessed {processed} PRs")


if __name__ == "__main__":
    main()
