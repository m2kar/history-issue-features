#!/usr/bin/env python3
"""合并所有 issue 输出，去重，构建依赖图，计算 rarity，输出 EDAzz 兼容格式.

用法:
    python3 merge.py [--output output/merged_history_v2_features.json]
    python3 merge.py --stats  # 仅打印统计
"""
import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from hashlib import sha1
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LEGACY_POOL = Path("/edazz/FeatureFuzz-SV/data/feature_pool.json")


# ── 收集 ──

def collect_features(repo_filter: str | None = None) -> tuple[list[dict], dict]:
    """遍历 issues/*/output/features.json, 收集所有 features."""
    all_features = []
    stats = {"issues_total": 0, "issues_with_features": 0, "issues_skipped": 0}

    issues_dir = ROOT / "issues"
    for issue_dir in sorted(issues_dir.iterdir()):
        if not issue_dir.is_dir():
            continue
        if repo_filter and not issue_dir.name.startswith(f"{repo_filter}-"):
            continue
        output = issue_dir / "output" / "features.json"
        if not output.is_file():
            continue
        stats["issues_total"] += 1
        data = json.loads(output.read_text())
        if isinstance(data, list):
            features = data
            skipped = False
        else:
            features = data.get("features", [])
            skipped = bool(data.get("skipped_reason"))
        if features:
            stats["issues_with_features"] += 1
            all_features.extend(features)
        elif skipped:
            stats["issues_skipped"] += 1

    return all_features, stats


# ── 去重 ──

def _normalize(s: str) -> str:
    return re.sub(r'\s+', ' ', (s or "").strip().lower())


def deduplicate(features: list[dict]) -> list[dict]:
    """按 normalize(description + snippet) 去重."""
    seen = set()
    result = []
    for feat in features:
        key = _normalize(feat.get("description", "")) + "\0" + _normalize(feat.get("snippet", ""))
        if key in seen:
            continue
        seen.add(key)
        result.append(feat)
    return result


def load_legacy_keys() -> set[tuple[str, str]]:
    """加载 legacy feature_pool.json 的 normalized keys 用于去重."""
    if not LEGACY_POOL.exists():
        return set()
    try:
        items = json.loads(LEGACY_POOL.read_text())
    except (json.JSONDecodeError, OSError):
        return set()
    keys = set()
    for item in items:
        desc = _normalize(item.get("description", ""))
        code = _normalize(item.get("code", ""))
        keys.add((desc, code))
    return keys


def _token_set(s: str) -> set[str]:
    return set(re.findall(r'\w+', s.lower()))


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def dedup_against_legacy(features: list[dict], legacy_keys: set[tuple[str, str]]) -> list[dict]:
    """与 legacy feature_pool.json 去重."""
    if not legacy_keys:
        return features

    # Build token sets for legacy entries
    legacy_tokens = []
    for desc, code in legacy_keys:
        legacy_tokens.append((_token_set(desc), _token_set(code)))

    result = []
    removed = 0
    for feat in features:
        desc_tokens = _token_set(feat.get("description", ""))
        snippet_tokens = _token_set(feat.get("snippet", ""))
        bug_id = feat.get("source_bug_id", "")

        is_dup = False
        for (leg_desc, leg_code), (leg_desc_tok, leg_code_tok) in zip(legacy_keys, legacy_tokens):
            # Same bug ID + high snippet similarity → duplicate
            snippet_sim = _jaccard(snippet_tokens, leg_code_tok)
            desc_sim = _jaccard(desc_tokens, leg_desc_tok)
            if snippet_sim > 0.8 and desc_sim > 0.6:
                is_dup = True
                break

        if is_dup:
            removed += 1
        else:
            result.append(feat)

    if removed:
        print(f"Removed {removed} features duplicating legacy pool")
    return result


# ── Feature ID ──

def make_feature_id(feat: dict) -> str:
    raw = f"history_v2\0{feat.get('description', '')}\0{feat.get('snippet', '')}"
    h = sha1(raw.encode()).hexdigest()[:12]
    return f"feat.history_v2.{h}"


# ── Feature Graph ──

def build_feature_graph(features: list[dict]) -> dict:
    """构建 feature_graph."""
    # 按 issue 分组
    issue_to_features = defaultdict(list)
    for feat in features:
        key = f"{feat.get('tool', '')}-{feat.get('source_bug_id', '')}"
        issue_to_features[key].append(feat["feature_id"])

    # Tag 依赖规则
    REQUIRES_MAP = {
        "extends": {"class"},
        "implements": {"interface"},
        "always_ff": {"posedge", "clock"},
        "always_comb": {"assign"},
        "generate": {"parameter"},
        "covergroup": {"class"},
        "randomize": {"class"},
    }

    graph = {}
    for feat in features:
        fid = feat["feature_id"]
        tags = set(feat.get("tags", []))
        issue_key = f"{feat.get('tool', '')}-{feat.get('source_bug_id', '')}"

        # requires
        requires = []
        for tag in tags:
            if tag in REQUIRES_MAP:
                req_tags = REQUIRES_MAP[tag]
                for other_fid in issue_to_features[issue_key]:
                    if other_fid == fid:
                        continue
                    other = next((f for f in features if f["feature_id"] == other_fid), None)
                    if other and req_tags & set(other.get("tags", [])):
                        if other_fid not in requires:
                            requires.append(other_fid)

        # co_occurs: same issue
        co_occurs = [f for f in issue_to_features[issue_key] if f != fid][:10]

        # rarity
        rarity = compute_rarity(feat, features)

        graph[fid] = {
            "requires": requires,
            "conflicts": [],
            "co_occurs": co_occurs,
            "rarity_score": round(rarity, 4),
        }

    return graph


def compute_rarity(feat: dict, all_features: list[dict]) -> float:
    """计算 rarity score."""
    # 1. construct_complexity (权重 0.40)
    complexity = feat.get("construct_complexity", 3)
    complexity_score = (complexity - 1) / 4.0

    # 2. tag 稀有度 (权重 0.30)
    tag_counts = Counter()
    for f in all_features:
        for t in f.get("tags", []):
            tag_counts[t] += 1
    total_tags = sum(tag_counts.values()) or 1
    feat_tags = feat.get("tags", [])
    if feat_tags:
        tag_rarities = [1.0 - (tag_counts.get(t, 0) / total_tags) for t in feat_tags]
        tag_score = sum(tag_rarities) / len(tag_rarities)
    else:
        tag_score = 0.5

    # 3. 冷门标签加成 (权重 0.15)
    cold_tags = {"streaming", "alias", "let", "bind", "chandle", "specify",
                 "primitive", "defparam", "supply", "randc", "covergroup",
                 "trireg", "wand", "wor", "tri0", "tri1"}
    cold_bonus = 0.8 if any(t in cold_tags for t in feat_tags) else 0.0

    # 4. 工具特异性 (权重 0.15)
    tool_score = 0.7 if feat.get("tool") == "circt" else 0.3

    rarity = (0.40 * complexity_score + 0.30 * min(tag_score, 1.0)
              + 0.15 * cold_bonus + 0.15 * tool_score)
    return max(0.05, min(rarity, 1.0))


# ── 输出 ──

def format_output(features: list[dict]) -> list[dict]:
    """转换为 EDAzz feature_dataset.json 兼容格式."""
    output = []
    for feat in features:
        tags = sorted(set(feat.get("tags", []) + [feat.get("category", "general")]))
        output.append({
            "feature_id": feat["feature_id"],
            "name": feat.get("name", "unnamed feature"),
            "category": feat.get("category", "general"),
            "description": feat.get("description", ""),
            "source": "history_v2",
            "tags": tags,
            "metadata": {
                "snippet": feat.get("snippet", ""),
                "source_bug_id": feat.get("source_bug_id"),
                "tool": feat.get("tool"),
                "issue_url": feat.get("issue_url"),
                "construct_complexity": feat.get("construct_complexity", 3),
                "ub_type": None,  # history issues are tool bugs, not language UB
                "error_pattern": feat.get("error_pattern"),
            },
        })
    return output


def build_dataset(output_features: list[dict], graph: dict,
                   source_label: str = "history_v2") -> dict:
    """构建 EDAzz per-source feature dataset (与 spec_features.json 同格式)."""
    return {
        "source": source_label,
        "total_features": len(output_features),
        "features": output_features,
        "feature_graph": graph,
        "build_info": {
            "built_at": datetime.now(timezone.utc).replace(microsecond=0)
                        .isoformat().replace("+00:00", "Z"),
            "builder": "history-issue-features/merge.py",
            "source_revision": "verilator+circt-github-issues",
        },
    }


# ── 主流程 ──

EDAZZ_HISTORY_DIR = Path("/edazz/EDAzz/data/feature_sources/history")


def _merge_repo(repo: str, args):
    # 1. 收集
    raw_features, stats = collect_features(repo_filter=repo)
    print(f"Collected: {len(raw_features)} features from {stats['issues_with_features']} issues")
    print(f"  (skipped: {stats['issues_skipped']}, no output: "
          f"{stats['issues_total'] - stats['issues_with_features'] - stats['issues_skipped']})")

    if not raw_features:
        print("No features to merge.")
        return

    # 2. 项目内去重
    deduped = deduplicate(raw_features)
    print(f"After internal dedup: {len(deduped)} ({len(raw_features) - len(deduped)} removed)")

    # 3. 与 legacy 去重
    legacy_keys = load_legacy_keys()
    if legacy_keys:
        print(f"Loaded {len(legacy_keys)} legacy features for dedup")
        deduped = dedup_against_legacy(deduped, legacy_keys)

    print(f"Final features: {len(deduped)}")

    # 4. 生成 ID
    for feat in deduped:
        feat["feature_id"] = make_feature_id(feat)

    # 5. 统计
    cat_dist = Counter(f.get("category", "?") for f in deduped)
    complexity_dist = Counter(f.get("construct_complexity", 0) for f in deduped)
    ub_count = sum(1 for f in deduped if f.get("ub_type"))

    print(f"\nCategory distribution: {dict(cat_dist)}")
    print(f"Complexity distribution: {dict(sorted(complexity_dist.items()))}")
    print(f"UB features: {ub_count}")

    if args.stats:
        return

    # 6. 构建 graph
    graph = build_feature_graph(deduped)
    requires_count = sum(len(v["requires"]) for v in graph.values())
    co_occurs_count = sum(len(v["co_occurs"]) for v in graph.values())
    print(f"\nGraph: {requires_count} requires edges, {co_occurs_count} co_occurs edges")

    # 7. 格式化输出
    output_features = format_output(deduped)

    # 8. 构建 dataset (per-source 格式)
    dataset = build_dataset(output_features, graph, source_label=f"history_v2_{repo}")

    # 9. 写入本地
    local_path = ROOT / "output" / f"{repo}_features.json"
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(json.dumps(dataset, indent=2, ensure_ascii=False) + "\n")
    print(f"\nLocal output: {local_path} ({len(output_features)} features)")

    # 10. 复制到 EDAzz
    edazz_path = EDAZZ_HISTORY_DIR / f"{repo}_features.json"
    EDAZZ_HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    edazz_path.write_text(json.dumps(dataset, indent=2, ensure_ascii=False) + "\n")
    print(f"Copied to: {edazz_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", help="Output path")
    parser.add_argument("--repo", choices=["verilator", "circt"],
                        help="Only merge specific repo")
    parser.add_argument("--stats", action="store_true", help="Print stats only")
    args = parser.parse_args()

    repos = [args.repo] if args.repo else ["verilator", "circt"]

    for repo in repos:
        print(f"\n{'='*60}")
        print(f"  Merging: {repo}")
        print(f"{'='*60}")
        _merge_repo(repo, args)


if __name__ == "__main__":
    main()
