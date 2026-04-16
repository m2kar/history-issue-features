#!/usr/bin/env python3
"""修复剩余的不合规 features.json 文件。"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ISSUES_DIR = ROOT / "issues"


def reconstruct_dict(issue_id: str, input_data: dict, features: list) -> dict:
    """从 issue_input.json 和特征列表重建标准 dict。"""
    return {
        "tool": input_data.get("tool", "unknown"),
        "issue_number": input_data.get("issue_number", 0),
        "title": input_data.get("title", ""),
        "features": features,
    }


def fix_feature(feat: dict) -> dict:
    """修复单个 feature 的缺失字段和非法字段。"""
    fixed = dict(feat)
    # 移除非法字段
    for key in ["root_cause", "trigger_scope"]:
        fixed.pop(key, None)
    # 补全缺失字段
    if "ub_type" not in fixed:
        fixed["ub_type"] = None
    if "construct_complexity" not in fixed:
        fixed["construct_complexity"] = 3
    return fixed


def main():
    fixed = 0
    errors = 0
    
    for feat_path in ISSUES_DIR.rglob("output/features.json"):
        issue_dir = feat_path.parent.parent
        issue_id = issue_dir.name
        input_path = issue_dir / "issue_input.json"
        
        try:
            data = json.loads(feat_path.read_text())
        except json.JSONDecodeError:
            errors += 1
            print(f"[ERROR] {issue_id}: invalid JSON")
            continue
        
        if not isinstance(data, dict):
            continue  # list 格式已经在上一轮修复
        
        needs_fix = False
        features = data.get("features", [])
        
        # 检查是否有缺失的 top-level 键或异常的键
        if "note" in data or "error" in data or "metadata" in data:
            needs_fix = True
        
        if not all(k in data for k in ["tool", "issue_number", "title"]):
            needs_fix = True
        
        # 检查 feature 内部问题
        if isinstance(features, list):
            for feat in features:
                if isinstance(feat, dict):
                    if "ub_type" not in feat or "root_cause" in feat or "trigger_scope" in feat:
                        needs_fix = True
                        break
        
        if not needs_fix:
            continue
        
        # 执行修复
        if not input_path.exists():
            print(f"[ERROR] {issue_id}: missing issue_input.json")
            errors += 1
            continue
        
        input_data = json.loads(input_path.read_text())
        
        # 如果存在 features list，先修复每个 feature
        if isinstance(features, list):
            fixed_features = [fix_feature(f) for f in features if isinstance(f, dict)]
        else:
            fixed_features = []
        
        wrapped = reconstruct_dict(issue_id, input_data, fixed_features)
        feat_path.write_text(
            json.dumps(wrapped, indent=2, ensure_ascii=False) + "\n"
        )
        print(f"[FIXED] {issue_id}: normalized dict with {len(fixed_features)} features")
        fixed += 1
    
    print(f"\nSummary: fixed={fixed}, errors={errors}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
