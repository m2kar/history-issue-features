#!/usr/bin/env python3
"""将 list 格式的 features.json 修复为 dict 格式。"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ISSUES_DIR = ROOT / "issues"

REQUIRED_FEATURE_KEYS = {
    "name", "category", "description", "snippet", "tags",
    "source_bug_id", "tool", "issue_url", "construct_complexity", "ub_type"
}


def wrap_list_to_dict(issue_id: str, input_data: dict, features: list) -> dict:
    """将 feature list 包装成标准 dict 格式。"""
    return {
        "tool": input_data.get("tool", "unknown"),
        "issue_number": input_data.get("issue_number", 0),
        "title": input_data.get("title", ""),
        "features": features,
    }


def main():
    fixed = 0
    errors = 0
    skipped = 0
    
    for feat_path in ISSUES_DIR.rglob("output/features.json"):
        issue_dir = feat_path.parent.parent
        issue_id = issue_dir.name
        input_path = issue_dir / "issue_input.json"
        
        try:
            data = json.loads(feat_path.read_text())
        except json.JSONDecodeError as e:
            print(f"[ERROR] {issue_id}: invalid JSON - {e}")
            errors += 1
            continue
        
        # 已经是 dict 格式，跳过
        if isinstance(data, dict):
            skipped += 1
            continue
        
        # list 格式，需要修复
        if isinstance(data, list):
            if not input_path.exists():
                print(f"[ERROR] {issue_id}: missing issue_input.json, cannot wrap list")
                errors += 1
                continue
            
            input_data = json.loads(input_path.read_text())
            wrapped = wrap_list_to_dict(issue_id, input_data, data)
            feat_path.write_text(
                json.dumps(wrapped, indent=2, ensure_ascii=False) + "\n"
            )
            print(f"[FIXED] {issue_id}: wrapped {len(data)} features into dict")
            fixed += 1
        else:
            print(f"[ERROR] {issue_id}: unexpected format {type(data)}")
            errors += 1
    
    print(f"\nSummary: fixed={fixed}, already_ok={skipped}, errors={errors}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
