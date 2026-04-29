#!/usr/bin/env python3
"""Generate multi-dimensional statistics for the feature dataset."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"

TOOL_FILES = {
    "verilator": OUT / "verilator_features.json",
    "circt":     OUT / "circt_features.json",
    "iverilog":  OUT / "iverilog_features.json",
    "yosys":     OUT / "yosys_features.json",
}


def load(path: Path) -> list[dict]:
    with path.open() as f:
        return json.load(f)["features"]


def pct(n, total):
    return f"{(n / total * 100):.2f}%" if total else "-"


def fmt_table(headers, rows):
    widths = [len(h) for h in headers]
    for r in rows:
        for i, c in enumerate(r):
            widths[i] = max(widths[i], len(str(c)))
    head = "| " + " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers)) + " |"
    sep  = "|" + "|".join("-" * (w + 2) for w in widths) + "|"
    body = "\n".join(
        "| " + " | ".join(str(c).ljust(widths[i]) for i, c in enumerate(r)) + " |"
        for r in rows
    )
    return "\n".join([head, sep, body])


def stats(nums):
    if not nums:
        return {"min": 0, "max": 0, "mean": 0, "median": 0}
    return {
        "min": min(nums),
        "max": max(nums),
        "mean": round(mean(nums), 2),
        "median": median(nums),
    }


def analyze():
    per_tool: dict[str, list[dict]] = {t: load(p) for t, p in TOOL_FILES.items()}
    all_feats = [f for fs in per_tool.values() for f in fs]

    lines: list[str] = []
    p = lines.append

    p("# Feature Dataset Statistics Report")
    p("")
    p("**Generated:** 2026-04-21")
    p(f"**Source files:** `output/{{verilator,circt,iverilog,yosys}}_features.json`")
    p("")
    p("---")
    p("")

    # 1. Overall summary
    p("## 1. Overall Summary")
    p("")
    total = len(all_feats)
    rows = []
    for tool, fs in per_tool.items():
        rows.append([tool, len(fs), pct(len(fs), total)])
    rows.append(["**Total**", total, "100.00%"])
    p(fmt_table(["Tool", "Features", "Share"], rows))
    p("")

    # Unique feature_id across tools
    id_counts = Counter(f["feature_id"] for f in all_feats)
    dup_ids = {k: v for k, v in id_counts.items() if v > 1}
    p(f"- **Unique `feature_id`s:** {len(id_counts)} ({pct(len(id_counts), total)} of total rows)")
    p(f"- **Duplicate `feature_id` rows (cross-tool):** {sum(v - 1 for v in dup_ids.values())} (collapsed from {len(dup_ids)} IDs)")

    # Unique by (description, snippet) signature across whole dataset
    sig = set()
    for f in all_feats:
        sig.add((f["description"].strip(), f["metadata"].get("snippet", "").strip()))
    p(f"- **Unique `(description, snippet)` signatures:** {len(sig)}")
    p("")

    # 2. Category distribution
    p("## 2. Category Distribution")
    p("")
    all_cats = sorted({f["category"] for f in all_feats})
    headers = ["Category"] + list(per_tool.keys()) + ["Total", "Share"]
    rows = []
    totals_by_cat = Counter(f["category"] for f in all_feats)
    per_tool_cat = {t: Counter(f["category"] for f in fs) for t, fs in per_tool.items()}
    for cat in sorted(all_cats, key=lambda c: -totals_by_cat[c]):
        row = [cat] + [per_tool_cat[t].get(cat, 0) for t in per_tool] + [totals_by_cat[cat], pct(totals_by_cat[cat], total)]
        rows.append(row)
    rows.append(["**Total**"] + [len(fs) for fs in per_tool.values()] + [total, "100.00%"])
    p(fmt_table(headers, rows))
    p("")

    # 3. Top tags
    p("## 3. Top Tags (Top 30 per tool, union)")
    p("")
    tag_counters = {t: Counter(tag for f in fs for tag in f.get("tags", [])) for t, fs in per_tool.items()}
    global_tags = Counter(tag for f in all_feats for tag in f.get("tags", []))
    p(f"- **Distinct tags (global):** {len(global_tags)}")
    p(f"- **Avg tags per feature:** {round(sum(global_tags.values()) / total, 2)}")
    p("")
    headers = ["Rank", "Tag", "Global", "verilator", "circt", "iverilog", "yosys"]
    rows = []
    for i, (tag, cnt) in enumerate(global_tags.most_common(30), 1):
        rows.append([i, tag, cnt] + [tag_counters[t].get(tag, 0) for t in per_tool])
    p(fmt_table(headers, rows))
    p("")

    # 4. Construct complexity
    p("## 4. Construct Complexity")
    p("")
    headers = ["Tool"] + [f"cc={i}" for i in range(1, 6)] + ["missing", "mean", "median"]
    rows = []
    for tool, fs in per_tool.items():
        ccs = [f["metadata"].get("construct_complexity") for f in fs]
        dist = Counter(ccs)
        nums = [c for c in ccs if isinstance(c, int)]
        s = stats(nums)
        row = [tool] + [dist.get(i, 0) for i in range(1, 6)] + [dist.get(None, 0), s["mean"], s["median"]]
        rows.append(row)
    # global
    ccs_all = [f["metadata"].get("construct_complexity") for f in all_feats]
    dist = Counter(ccs_all)
    nums = [c for c in ccs_all if isinstance(c, int)]
    s = stats(nums)
    rows.append(["**Total**"] + [dist.get(i, 0) for i in range(1, 6)] + [dist.get(None, 0), s["mean"], s["median"]])
    p(fmt_table(headers, rows))
    p("")

    # 5. UB type distribution
    p("## 5. UB Type Distribution")
    p("")
    ubs = Counter(f["metadata"].get("ub_type") for f in all_feats)
    rows = [[k if k is not None else "(null)", v, pct(v, total)] for k, v in ubs.most_common()]
    p(fmt_table(["ub_type", "count", "share"], rows))
    p("")

    # 6. Error pattern
    p("## 6. Error Pattern Distribution")
    p("")
    headers = ["error_pattern"] + list(per_tool.keys()) + ["Total", "Share"]
    ep_all = Counter(f["metadata"].get("error_pattern") for f in all_feats)
    ep_tool = {t: Counter(f["metadata"].get("error_pattern") for f in fs) for t, fs in per_tool.items()}
    p(f"- **Distinct error patterns:** {len(ep_all)}")
    p("")
    p("### Top 25 error patterns")
    p("")
    rows = []
    top25 = ep_all.most_common(25)
    shown = {k for k, _ in top25}
    for ep, cnt in top25:
        label = ep if ep is not None else "(null)"
        row = [label] + [ep_tool[t].get(ep, 0) for t in per_tool] + [cnt, pct(cnt, total)]
        rows.append(row)
    # Aggregate long tail
    tail_cnt = sum(cnt for ep, cnt in ep_all.items() if ep not in shown)
    if tail_cnt:
        tail_per_tool = [
            sum(v for k, v in ep_tool[t].items() if k not in shown)
            for t in per_tool
        ]
        rows.append([f"_other ({len(ep_all) - len(shown)} patterns)_"] + tail_per_tool + [tail_cnt, pct(tail_cnt, total)])
    p(fmt_table(headers, rows))
    p("")

    # 7. Snippet length
    p("## 7. Snippet Length (characters / lines)")
    p("")
    headers = ["Tool", "char min", "char max", "char mean", "char median", "line min", "line max", "line mean", "line median"]
    rows = []
    for tool, fs in per_tool.items():
        chars = [len(f["metadata"].get("snippet", "")) for f in fs]
        lines_ = [f["metadata"].get("snippet", "").count("\n") + 1 for f in fs if f["metadata"].get("snippet")]
        sc, sl = stats(chars), stats(lines_)
        rows.append([tool, sc["min"], sc["max"], sc["mean"], sc["median"], sl["min"], sl["max"], sl["mean"], sl["median"]])
    # global
    chars = [len(f["metadata"].get("snippet", "")) for f in all_feats]
    lines_ = [f["metadata"].get("snippet", "").count("\n") + 1 for f in all_feats if f["metadata"].get("snippet")]
    sc, sl = stats(chars), stats(lines_)
    rows.append(["**Total**", sc["min"], sc["max"], sc["mean"], sc["median"], sl["min"], sl["max"], sl["mean"], sl["median"]])
    p(fmt_table(headers, rows))
    p("")

    # 8. Features per issue
    p("## 8. Features per Source Issue")
    p("")
    headers = ["Tool", "issues", "features", "min", "max", "mean", "median"]
    rows = []
    for tool, fs in per_tool.items():
        by_issue = Counter(f["metadata"].get("source_bug_id") for f in fs)
        cnts = list(by_issue.values())
        s = stats(cnts)
        rows.append([tool, len(by_issue), len(fs), s["min"], s["max"], s["mean"], s["median"]])
    by_issue_all = Counter((f["metadata"].get("tool"), f["metadata"].get("source_bug_id")) for f in all_feats)
    cnts = list(by_issue_all.values())
    s = stats(cnts)
    rows.append(["**Total**", len(by_issue_all), len(all_feats), s["min"], s["max"], s["mean"], s["median"]])
    p(fmt_table(headers, rows))
    p("")

    # Top-20 issues by feature count
    p("### 8.1 Top-20 Issues by Feature Count")
    p("")
    by_issue_detailed = Counter()
    issue_tool = {}
    for f in all_feats:
        key = (f["metadata"].get("tool"), f["metadata"].get("source_bug_id"))
        by_issue_detailed[key] += 1
        issue_tool[key] = f["metadata"].get("issue_url", "")
    rows = []
    for i, ((tool, sid), cnt) in enumerate(by_issue_detailed.most_common(20), 1):
        rows.append([i, tool, sid, cnt, issue_tool[(tool, sid)]])
    p(fmt_table(["Rank", "tool", "source_bug_id", "features", "url"], rows))
    p("")

    # 9. Description length
    p("## 9. Description Length (characters)")
    p("")
    headers = ["Tool", "min", "max", "mean", "median"]
    rows = []
    for tool, fs in per_tool.items():
        lens = [len(f["description"]) for f in fs]
        s = stats(lens)
        rows.append([tool, s["min"], s["max"], s["mean"], s["median"]])
    lens = [len(f["description"]) for f in all_feats]
    s = stats(lens)
    rows.append(["**Total**", s["min"], s["max"], s["mean"], s["median"]])
    p(fmt_table(headers, rows))
    p("")

    # 10. Description prefix compliance ("Code should include")
    p("## 10. Description Format Compliance")
    p("")
    p("Project requires every description to begin with `Code should include`.")
    p("")
    rows = []
    for tool, fs in per_tool.items():
        ok = sum(1 for f in fs if f["description"].startswith("Code should include"))
        rows.append([tool, ok, len(fs) - ok, pct(ok, len(fs))])
    ok = sum(1 for f in all_feats if f["description"].startswith("Code should include"))
    rows.append(["**Total**", ok, len(all_feats) - ok, pct(ok, len(all_feats))])
    p(fmt_table(["Tool", "compliant", "non-compliant", "compliance rate"], rows))
    p("")

    # 11. Cross-tool overlap by feature_id
    p("## 11. Cross-tool Overlap")
    p("")
    id_tools = defaultdict(set)
    for f in all_feats:
        id_tools[f["feature_id"]].add(f["metadata"].get("tool"))
    overlap_counts = Counter(frozenset(v) for v in id_tools.values() if len(v) > 1)
    p(f"- **Features appearing in multiple tools:** {sum(overlap_counts.values())}")
    if overlap_counts:
        rows = [[" + ".join(sorted(k)), v] for k, v in overlap_counts.most_common()]
        p("")
        p(fmt_table(["tool set", "shared features"], rows))
    p("")

    # 12. Name length / uniqueness
    p("## 12. Feature Name Uniqueness")
    p("")
    rows = []
    for tool, fs in per_tool.items():
        names = [f["name"] for f in fs]
        uniq = len(set(names))
        rows.append([tool, len(names), uniq, len(names) - uniq])
    names = [f["name"] for f in all_feats]
    uniq = len(set(names))
    rows.append(["**Total**", len(names), uniq, len(names) - uniq])
    p(fmt_table(["Tool", "features", "unique names", "collisions"], rows))
    p("")

    # 13. Source issue reference to raw datasets
    p("## 13. Issue Coverage vs Raw Corpus")
    p("")
    raw_counts = {
        "verilator": "raw/verilator.jsonl",
        "circt":     "raw/circt.jsonl",
        "iverilog":  "raw/iverilog.jsonl",
        "yosys":     "raw/yosys.jsonl",
    }
    rows = []
    for tool, fs in per_tool.items():
        path = ROOT / raw_counts[tool]
        if path.exists():
            with path.open() as f_:
                raw_total = sum(1 for _ in f_)
        else:
            raw_total = None
        by_issue = {f["metadata"].get("source_bug_id") for f in fs}
        rows.append([tool, raw_total if raw_total is not None else "n/a", len(by_issue),
                     pct(len(by_issue), raw_total) if raw_total else "n/a"])
    p(fmt_table(["Tool", "raw issues", "issues w/ features", "coverage"], rows))
    p("")

    p("---")
    p("")
    p("_Generated by `scripts/analyze_dataset.py`._")
    p("")
    return "\n".join(lines)


def main():
    text = analyze()
    out_path = ROOT / "docs" / "04_dataset_statistics.md"
    out_path.write_text(text)
    print(f"wrote {out_path} ({len(text)} bytes)")


if __name__ == "__main__":
    main()
