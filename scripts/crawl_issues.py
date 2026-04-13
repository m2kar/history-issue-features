#!/usr/bin/env python3
"""从 Verilator/CIRCT GitHub 仓库爬取 issue/PR 原始数据.

用法:
    python3 scripts/crawl_issues.py                    # 增量爬取
    python3 scripts/crawl_issues.py --full             # 全量 (复制基线 + 增量)
    python3 scripts/crawl_issues.py --repo verilator   # 仅爬取 verilator
    python3 scripts/crawl_issues.py --repo circt       # 仅爬取 circt

数据格式: 每行 "number\\tJSON", 与 /edazz/mirtl-pocs/issues/ 一致.
频率控制: 2000 requests/hour, 每请求间隔 1.8s.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"

REPOS = {
    "verilator": "verilator/verilator",
    "circt": "llvm/circt",
}

BASELINE_DIR = Path("/edazz/mirtl-pocs/issues")
SLEEP_INTERVAL = 1.8  # seconds between API pages


def load_config() -> dict:
    cfg_path = ROOT / "config.yaml"
    if cfg_path.exists():
        import yaml
        return yaml.safe_load(cfg_path.read_text()) or {}
    return {}


def load_crawl_state() -> dict:
    state_path = RAW_DIR / "crawl_state.json"
    if state_path.exists():
        return json.loads(state_path.read_text())
    return {}


def save_crawl_state(state: dict):
    state_path = RAW_DIR / "crawl_state.json"
    state_path.write_text(json.dumps(state, indent=2) + "\n")


def copy_baseline(tool: str) -> bool:
    """复制基线数据到 raw/ 目录."""
    src = BASELINE_DIR / f"{tool}.jsonl"
    dst = RAW_DIR / f"{tool}.jsonl"
    if not src.exists():
        print(f"  Baseline not found: {src}")
        return False
    if dst.exists():
        print(f"  raw/{tool}.jsonl already exists, skipping baseline copy")
        return True
    print(f"  Copying baseline: {src} -> {dst}")
    shutil.copy2(src, dst)
    return True


def get_existing_numbers(tool: str) -> set[int]:
    """读取已有 JSONL 中的 issue numbers."""
    path = RAW_DIR / f"{tool}.jsonl"
    if not path.exists():
        return set()
    numbers = set()
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t", 1)
            if parts[0].isdigit():
                numbers.add(int(parts[0]))
    return numbers


def get_latest_updated_at(tool: str) -> str | None:
    """从已有数据中找最新的 updated_at 时间."""
    path = RAW_DIR / f"{tool}.jsonl"
    if not path.exists():
        return None
    latest = None
    with open(path) as f:
        for line in f:
            parts = line.strip().split("\t", 1)
            if len(parts) < 2:
                continue
            try:
                d = json.loads(parts[1])
                updated = d.get("updated_at")
                if updated and (latest is None or updated > latest):
                    latest = updated
            except json.JSONDecodeError:
                continue
    return latest


def crawl_incremental(tool: str, repo: str, since: str | None = None):
    """增量爬取: 获取 since 之后更新的 issue/PR."""
    existing = get_existing_numbers(tool)
    print(f"  Existing entries: {len(existing)}")

    # 构建 API URL
    url = f"/repos/{repo}/issues?state=all&sort=updated&direction=asc&per_page=100"
    if since:
        url += f"&since={since}"
        print(f"  Fetching updates since: {since}")
    else:
        print(f"  No since date, fetching all (this may take a while)")

    # 使用 gh api 逐页获取
    output_path = RAW_DIR / f"{tool}.jsonl"
    new_count = 0
    update_count = 0
    page = 1

    env = os.environ.copy()
    env["GH_NO_UPDATE_NOTIFIER"] = "1"
    env["GH_PROMPT_DISABLED"] = "1"

    while True:
        page_url = f"{url}&page={page}"
        print(f"  Page {page}...", end=" ", flush=True)

        try:
            result = subprocess.run(
                ["gh", "api", page_url],
                capture_output=True, text=True, timeout=60, env=env,
            )
        except subprocess.TimeoutExpired:
            print("timeout, retrying after 10s...")
            time.sleep(10)
            continue

        if result.returncode != 0:
            print(f"error: {result.stderr.strip()}")
            # Rate limit?
            if "rate limit" in result.stderr.lower() or "403" in result.stderr:
                print("  Rate limited! Waiting 60s...")
                time.sleep(60)
                continue
            break

        try:
            items = json.loads(result.stdout)
        except json.JSONDecodeError:
            print(f"invalid JSON response")
            break

        if not items:
            print("empty page, done.")
            break

        with open(output_path, "a") as f:
            for item in items:
                num = item["number"]
                line = f"{num}\t{json.dumps(item, ensure_ascii=False)}\n"
                if num in existing:
                    update_count += 1
                    # 对于已存在的 issue, 我们追加新版本 (merge 时取最新)
                else:
                    new_count += 1
                    existing.add(num)
                f.write(line)

        print(f"{len(items)} items (new: {new_count}, updated: {update_count})")

        if len(items) < 100:
            print("  Last page reached.")
            break

        page += 1
        time.sleep(SLEEP_INTERVAL)

    return new_count, update_count


def deduplicate_jsonl(tool: str):
    """去重: 同一个 number 保留最后出现的版本."""
    path = RAW_DIR / f"{tool}.jsonl"
    if not path.exists():
        return

    entries: dict[int, str] = {}  # number -> full line
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t", 1)
            if parts[0].isdigit():
                entries[int(parts[0])] = line

    # 按 number 降序写回
    with open(path, "w") as f:
        for num in sorted(entries, reverse=True):
            f.write(entries[num] + "\n")

    print(f"  Deduplicated: {len(entries)} unique entries for {tool}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="Full crawl (copy baseline + incremental)")
    parser.add_argument("--repo", choices=["verilator", "circt"], help="Only crawl specific repo")
    parser.add_argument("--dedup-only", action="store_true", help="Only deduplicate existing data")
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    state = load_crawl_state()

    tools = [args.repo] if args.repo else list(REPOS.keys())

    for tool in tools:
        repo = REPOS[tool]
        print(f"\n{'='*60}")
        print(f"Processing: {tool} ({repo})")
        print(f"{'='*60}")

        if args.dedup_only:
            deduplicate_jsonl(tool)
            continue

        # 全量模式: 先复制基线
        if args.full:
            copy_baseline(tool)

        # 确定 since 时间
        since = state.get(f"{tool}_last_updated")
        if not since:
            since = get_latest_updated_at(tool)

        # 增量爬取
        new_count, update_count = crawl_incremental(tool, repo, since)

        # 去重
        deduplicate_jsonl(tool)

        # 更新状态
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        state[f"{tool}_last_updated"] = now
        state[f"{tool}_last_crawl"] = now
        total = len(get_existing_numbers(tool))
        state[f"{tool}_total"] = total
        print(f"  Total entries: {total}")

    save_crawl_state(state)
    print(f"\nCrawl state saved to: {RAW_DIR / 'crawl_state.json'}")


if __name__ == "__main__":
    main()
