#!/usr/bin/env python3
"""批量执行所有 issue 的特征提取。

用法:
    python3 run-all.py [--config config.yaml] [--limit 10] [--repo verilator]
"""
import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent


# -- 配置 --

@dataclass
class Provider:
    name: str
    env: dict[str, str] = field(default_factory=dict)
    concurrency: int = 1


@dataclass
class Config:
    timeout: int = 600
    subagent_parallelism: int = 2
    providers: list[Provider] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: str) -> "Config":
        import yaml
        with open(path) as f:
            raw = yaml.safe_load(f)
        providers = []
        for p in raw.get("providers") or []:
            env = {str(k): str(v) for k, v in (p.get("env") or {}).items()}
            concurrency = int(p.get("concurrency", 1))
            providers.append(Provider(name=p.get("name", "unnamed"), env=env, concurrency=concurrency))
        return cls(
            timeout=int(raw.get("timeout", 600)),
            subagent_parallelism=int(raw.get("subagent_parallelism", 2)),
            providers=providers,
        )


# -- Worker Pool --

@dataclass
class Job:
    issue_id: str
    proc: subprocess.Popen
    slot_idx: int
    start_ts: float


@dataclass
class Slot:
    index: int
    provider: Provider | None
    job: Job | None = None
    available_at: float = 0.0


class WorkerPool:
    def __init__(self, config: Config):
        self.config = config
        slots = []
        if config.providers:
            for provider in config.providers:
                for _ in range(provider.concurrency):
                    slots.append(Slot(index=len(slots), provider=provider))
        else:
            slots.append(Slot(index=0, provider=None))
        self.slots = slots

    @property
    def parallel(self) -> int:
        return len(self.slots)

    def find_free_slot(self) -> Slot | None:
        now = time.time()
        for slot in self.slots:
            if slot.job is not None and slot.job.proc.poll() is not None:
                self._report_done(slot)
            if slot.job is None and now >= slot.available_at:
                return slot
        return None

    def wait_for_free_slot(self) -> Slot:
        while True:
            slot = self.find_free_slot()
            if slot is not None:
                return slot
            time.sleep(1)

    def launch(self, slot: Slot, issue_id: str, idx: int, total: int):
        env = os.environ.copy()
        if slot.provider and slot.provider.env:
            env.update(slot.provider.env)
        env["SUBAGENT_PARALLELISM"] = str(self.config.subagent_parallelism)

        log_path = ROOT / "logs" / f"run-{issue_id}.log"
        cmd = [sys.executable, str(ROOT / "run-issue.py"), issue_id]

        provider_tag = f" [{slot.provider.name}/slot{slot.index}]" if slot.provider else ""
        print(f"[{_ts()}] >>> {issue_id} ({idx}/{total}){provider_tag}")

        with open(log_path, "w") as log_f:
            proc = subprocess.Popen(cmd, stdout=log_f, stderr=subprocess.STDOUT, env=env)

        slot.job = Job(issue_id=issue_id, proc=proc, slot_idx=slot.index, start_ts=time.time())

    def _report_done(self, slot: Slot):
        job = slot.job
        if not job:
            return
        dur = time.time() - job.start_ts
        rc = job.proc.returncode
        status = "done" if rc == 0 else "failed"
        mark = "OK" if rc == 0 else "FAIL"
        print(f"[{_ts()}] {mark} {job.issue_id} ({dur:.0f}s)")
        slot.job = None
        slot.available_at = time.time() + 5  # 5s gap between launches

    def drain(self):
        for slot in self.slots:
            if slot.job:
                slot.job.proc.wait()
                self._report_done(slot)


def _ts() -> str:
    return time.strftime("%H:%M:%S")


# -- 主流程 --

def discover_pending(repo_filter: str | None = None) -> list[str]:
    """发现需要处理的 issue (有 issue_input.json 但无 output/features.json)."""
    issues_dir = ROOT / "issues"
    if not issues_dir.exists():
        return []

    pending = []
    for issue_dir in sorted(issues_dir.iterdir()):
        if not issue_dir.is_dir():
            continue
        # repo 过滤
        if repo_filter and not issue_dir.name.startswith(f"{repo_filter}-"):
            continue
        input_path = issue_dir / "issue_input.json"
        output_path = issue_dir / "output" / "features.json"
        if input_path.exists() and not output_path.exists():
            pending.append(issue_dir.name)

    return pending


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of issues to process")
    parser.add_argument("--repo", choices=["verilator", "circt"], help="Only process specific repo")
    args = parser.parse_args()

    config = Config.from_yaml(args.config)
    (ROOT / "logs").mkdir(exist_ok=True)

    # 发现待处理的 issue
    pending = discover_pending(args.repo)
    total_issues = len(list((ROOT / "issues").iterdir())) if (ROOT / "issues").exists() else 0
    done = total_issues - len(pending)

    print(f"Total issues: {total_issues}")
    print(f"Pending: {len(pending)} (already done: {done})")

    if not pending:
        print("All issues already processed.")
        return

    if args.limit:
        pending = pending[:args.limit]
        print(f"Limited to: {len(pending)} issues")

    # 执行
    pool = WorkerPool(config)
    print(f"Workers: {pool.parallel} provider(s), {config.subagent_parallelism} subagents/issue")
    print()

    for idx, issue_id in enumerate(pending, 1):
        slot = pool.wait_for_free_slot()
        pool.launch(slot, issue_id, idx, len(pending))

    pool.drain()

    # 汇总
    final_pending = discover_pending(args.repo)
    newly_done = len(pending) - len([p for p in pending if p in final_pending])
    print(f"\nCompleted this run: {newly_done}/{len(pending)}")
    print(f"Remaining: {len(final_pending)}")


if __name__ == "__main__":
    main()
