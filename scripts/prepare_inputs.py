#!/usr/bin/env python3
"""将原始 JSONL 数据预处理为 agent 输入.

用法:
    python3 scripts/prepare_inputs.py                      # 处理所有
    python3 scripts/prepare_inputs.py --repo verilator     # 仅 verilator
    python3 scripts/prepare_inputs.py --sample 20          # 随机抽样检查
    python3 scripts/prepare_inputs.py --stats              # 仅统计
"""
import argparse
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"
ISSUES_DIR = ROOT / "issues"

REPOS = {
    "verilator": "verilator/verilator",
    "circt": "llvm/circt",
    "iverilog": "steveicarus/iverilog",
    "yosys": "YosysHQ/yosys",
}

# -- 排除标签 (精确匹配) --
EXCLUDE_LABELS_VERILATOR = {
    "area: documentation",
    "area: build system",
    "type: feature request",
    "type: question",
    "type: support",
}

EXCLUDE_LABELS_CIRCT = {
    "documentation",
    "question",
}

EXCLUDE_LABELS_IVERILOG = {
    "Need info",
    "Need test program",
    "Obsolete",
    "VHDL",
    "VPI",
}

EXCLUDE_LABELS_YOSYS = {
    "question",
    "feature-request",
    "documentation",
    "invalid",
    "duplicate",
    "needs-info",
    "build-system",
    "discuss",
    "status-superseded",
}

# -- SV 关键词 (用于判断 body 是否包含 SV 内容) --
SV_KEYWORDS = {
    "module", "endmodule", "always", "always_ff", "always_comb", "always_latch",
    "assign", "wire", "logic", "reg", "input", "output", "inout",
    "initial", "final", "generate", "endgenerate", "interface", "endinterface",
    "class", "endclass", "function", "endfunction", "task", "endtask",
    "assert", "assume", "cover", "property", "sequence",
    "typedef", "struct", "union", "enum", "package", "endpackage",
    "parameter", "localparam", "genvar", "case", "endcase",
    "posedge", "negedge", "begin", "end", "fork", "join",
}

# -- CIRCT-specific 关键词 --
CIRCT_SV_KEYWORDS = {"circt-verilog", "ImportVerilog", "slang", "sv-to-hw"}


def extract_code_blocks(body: str) -> list[str]:
    """从 body 中提取 fenced code blocks (仅保留含 SV 内容的)."""
    pattern = r"```(?:\w*)\s*\n(.*?)```"
    blocks = re.findall(pattern, body, re.DOTALL)
    # 过滤掉非代码内容 (如纯文本描述、shell 输出等)
    result = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        # 至少包含一个 SV 关键词或看起来像代码 (有分号、括号等)
        block_lower = block.lower()
        has_sv = any(kw in block_lower for kw in (
            "module", "endmodule", "wire", "logic", "reg", "assign",
            "always", "initial", "function", "endfunction", "task",
            "class", "endclass", "interface", "begin", "end",
            "input", "output", "parameter", "typedef", "struct",
            "generate", "assert", "package", "import",
        ))
        has_code_syntax = ";" in block or "endmodule" in block_lower
        # Reject blocks that look like prose (high ratio of spaces/letters, no semicolons)
        is_prose = (block.count(".") > block.count(";") + 3
                    and "###" in block or "- " in block.split("\n")[0])
        if (has_sv or has_code_syntax) and not is_prose:
            result.append(block)
    return result


def has_sv_content(body: str) -> bool:
    """判断 body 是否包含 SystemVerilog 相关内容."""
    if not body:
        return False
    body_lower = body.lower()
    # 有 SV 代码块
    code_blocks = extract_code_blocks(body)
    for block in code_blocks:
        block_words = set(re.findall(r'\b\w+\b', block.lower()))
        if block_words & SV_KEYWORDS:
            return True
    # body 中直接出现 SV 关键词 (至少 2 个不同关键词)
    body_words = set(re.findall(r'\b\w+\b', body_lower))
    sv_matches = body_words & SV_KEYWORDS
    if len(sv_matches) >= 2:
        return True
    return False


def has_circt_verilog_content(body: str, title: str) -> bool:
    """判断是否与 circt-verilog / ImportVerilog 相关."""
    text = f"{title}\n{body}".lower()
    return any(kw.lower() in text for kw in CIRCT_SV_KEYWORDS)


def should_include_verilator(item: dict) -> tuple[bool, str]:
    """判断 verilator issue/PR 是否应该纳入."""
    labels = {l["name"] for l in item.get("labels", [])}
    if labels & EXCLUDE_LABELS_VERILATOR:
        return False, f"excluded label: {labels & EXCLUDE_LABELS_VERILATOR}"

    body = item.get("body") or ""
    title = item.get("title") or ""
    is_pr = item.get("pull_request") is not None

    if is_pr:
        # PR: title 含 fix/Fix, 或 body 含 SV 内容
        title_lower = title.lower()
        if ("fix" in title_lower or "bug" in title_lower) and has_sv_content(body):
            return True, "PR with fix + SV content"
        if has_sv_content(body):
            return True, "PR with SV content"
        # PR body 引用了 issue
        if re.search(r'(?:fix|close|resolve)s?\s+#\d+', body, re.IGNORECASE):
            return True, "PR fixing an issue"
        return False, "PR without SV content or fix reference"

    # Issue
    if has_sv_content(body):
        return True, "issue with SV content"
    if extract_code_blocks(body):
        return True, "issue with code blocks"
    return False, "issue without SV content"


def should_include_iverilog(item: dict) -> tuple[bool, str]:
    """判断 iverilog issue/PR 是否应该纳入."""
    labels = {l["name"] for l in item.get("labels", [])}
    if labels & EXCLUDE_LABELS_IVERILOG:
        return False, f"excluded label: {labels & EXCLUDE_LABELS_IVERILOG}"

    body = item.get("body") or ""
    title = item.get("title") or ""
    is_pr = item.get("pull_request") is not None

    if is_pr:
        title_lower = title.lower()
        if ("fix" in title_lower or "bug" in title_lower) and has_sv_content(body):
            return True, "PR with fix + SV content"
        if has_sv_content(body):
            return True, "PR with SV content"
        if re.search(r'(?:fix|close|resolve)s?\s+#\d+', body, re.IGNORECASE):
            return True, "PR fixing an issue"
        return False, "PR without SV content or fix reference"

    if has_sv_content(body):
        return True, "issue with SV content"
    if extract_code_blocks(body):
        return True, "issue with code blocks"
    return False, "issue without SV content"


def should_include_yosys(item: dict) -> tuple[bool, str]:
    """判断 yosys issue/PR 是否应该纳入."""
    labels = {l["name"] for l in item.get("labels", [])}
    if labels & EXCLUDE_LABELS_YOSYS:
        return False, f"excluded label: {labels & EXCLUDE_LABELS_YOSYS}"

    body = item.get("body") or ""
    title = item.get("title") or ""
    is_pr = item.get("pull_request") is not None

    if is_pr:
        title_lower = title.lower()
        if ("fix" in title_lower or "bug" in title_lower) and has_sv_content(body):
            return True, "PR with fix + SV content"
        if has_sv_content(body):
            return True, "PR with SV content"
        if re.search(r'(?:fix|close|resolve)s?\s+#\d+', body, re.IGNORECASE):
            return True, "PR fixing an issue"
        return False, "PR without SV content or fix reference"

    if has_sv_content(body):
        return True, "issue with SV content"
    if extract_code_blocks(body):
        return True, "issue with code blocks"
    # SystemVerilog label
    if "SystemVerilog" in labels:
        return True, "SystemVerilog label"
    return False, "issue without SV content"


def should_include_circt(item: dict) -> tuple[bool, str]:
    """判断 circt issue/PR 是否应该纳入."""
    labels = {l["name"] for l in item.get("labels", [])}
    if labels & EXCLUDE_LABELS_CIRCT:
        return False, f"excluded label: {labels & EXCLUDE_LABELS_CIRCT}"

    body = item.get("body") or ""
    title = item.get("title") or ""

    # circt-verilog 相关
    if has_circt_verilog_content(body, title):
        return True, "circt-verilog related"
    # label 包含 verilog/SV 相关
    label_text = " ".join(labels).lower()
    if any(kw in label_text for kw in ("verilog", "systemverilog", "sv", "slang")):
        return True, "SV-related label"
    # body 含 SV 内容
    if has_sv_content(body):
        return True, "issue with SV content"
    # 含 .sv/.v 文件引用
    if re.search(r'\b\w+\.(sv|v)\b', body):
        return True, "references .sv/.v files"
    return False, "no SV/Verilog content"


def make_issue_input(tool: str, item: dict) -> dict:
    """生成 issue_input.json 内容."""
    body = item.get("body") or ""
    is_pr = item.get("pull_request") is not None
    return {
        "tool": tool,
        "type": "pull_request" if is_pr else "issue",
        "issue_number": item["number"],
        "issue_url": item.get("html_url", f"https://github.com/{REPOS[tool]}/issues/{item['number']}"),
        "title": item.get("title", ""),
        "body": body,
        "labels": [l["name"] for l in item.get("labels", [])],
        "state": item.get("state", "unknown"),
        "created_at": (item.get("created_at") or "")[:10],
        "closed_at": (item.get("closed_at") or "")[:10] if item.get("closed_at") else None,
        "code_blocks": extract_code_blocks(body),
        "linked_pr": None,
        "pr_files": None,
        "pr_test_files": None,
    }


def load_jsonl(tool: str) -> list[dict]:
    """加载 JSONL 文件."""
    path = RAW_DIR / f"{tool}.jsonl"
    if not path.exists():
        print(f"  File not found: {path}", file=sys.stderr)
        return []
    items = []
    with open(path) as f:
        for line in f:
            parts = line.strip().split("\t", 1)
            if len(parts) < 2:
                continue
            try:
                items.append(json.loads(parts[1]))
            except json.JSONDecodeError:
                continue
    return items


def process_tool(tool: str, stats_only: bool = False) -> tuple[int, int, list[dict], list[dict]]:
    """处理单个工具的数据. 返回 (included, excluded, included_items, excluded_items)."""
    items = load_jsonl(tool)
    print(f"  Loaded {len(items)} raw entries")

    filter_map = {
        "verilator": should_include_verilator,
        "circt": should_include_circt,
        "iverilog": should_include_iverilog,
        "yosys": should_include_yosys,
    }
    filter_fn = filter_map[tool]

    included = []
    excluded = []
    for item in items:
        ok, reason = filter_fn(item)
        item["_filter_reason"] = reason
        if ok:
            included.append(item)
        else:
            excluded.append(item)

    print(f"  Included: {len(included)}")
    print(f"  Excluded: {len(excluded)}")

    if stats_only:
        # 打印排除原因分布
        reasons = {}
        for item in excluded:
            r = item["_filter_reason"]
            reasons[r] = reasons.get(r, 0) + 1
        print(f"  Exclusion reasons:")
        for reason, count in sorted(reasons.items(), key=lambda x: -x[1]):
            print(f"    {count:5d}  {reason}")
        return len(included), len(excluded), included, excluded

    # 生成 issue_input.json
    created = 0
    skipped = 0
    for item in included:
        num = item["number"]
        issue_dir = ISSUES_DIR / f"{tool}-{num}"
        input_path = issue_dir / "issue_input.json"
        if input_path.exists():
            skipped += 1
            continue
        issue_dir.mkdir(parents=True, exist_ok=True)
        (issue_dir / "workspace").mkdir(exist_ok=True)
        (issue_dir / "output").mkdir(exist_ok=True)
        input_data = make_issue_input(tool, item)
        input_path.write_text(json.dumps(input_data, indent=2, ensure_ascii=False) + "\n")
        created += 1

    print(f"  Created: {created} issue_input.json files (skipped {skipped} existing)")
    return len(included), len(excluded), included, excluded


def sample_check(included: list[dict], excluded: list[dict], tool: str, n: int = 20):
    """随机抽样检查筛选质量."""
    print(f"\n  === Sample check for {tool} ===")
    print(f"\n  --- {n} sampled INCLUDED items ---")
    sample_inc = random.sample(included, min(n, len(included)))
    for item in sample_inc:
        is_pr = "PR" if item.get("pull_request") else "Issue"
        body = (item.get("body") or "")[:100].replace("\n", " ")
        print(f"    #{item['number']} [{is_pr}] {item.get('title', '')[:60]}")
        print(f"      Reason: {item['_filter_reason']}")
        print(f"      Body: {body}...")

    print(f"\n  --- {n} sampled EXCLUDED items ---")
    sample_exc = random.sample(excluded, min(n, len(excluded)))
    for item in sample_exc:
        is_pr = "PR" if item.get("pull_request") else "Issue"
        body = (item.get("body") or "")[:100].replace("\n", " ")
        print(f"    #{item['number']} [{is_pr}] {item.get('title', '')[:60]}")
        print(f"      Reason: {item['_filter_reason']}")
        print(f"      Body: {body}...")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", choices=list(REPOS.keys()))
    parser.add_argument("--sample", type=int, help="Sample N items for quality check")
    parser.add_argument("--stats", action="store_true", help="Stats only, no file creation")
    args = parser.parse_args()

    ISSUES_DIR.mkdir(parents=True, exist_ok=True)

    tools = [args.repo] if args.repo else list(REPOS.keys())

    for tool in tools:
        print(f"\n{'='*60}")
        print(f"Processing: {tool}")
        print(f"{'='*60}")

        n_inc, n_exc, included, excluded = process_tool(tool, stats_only=args.stats)

        if args.sample:
            sample_check(included, excluded, tool, args.sample)

    print(f"\nDone. Issue directories at: {ISSUES_DIR}")


if __name__ == "__main__":
    main()
