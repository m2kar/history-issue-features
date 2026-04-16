#!/usr/bin/env python3
"""校验所有 issues/*/output/features.json 的格式合规性。"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ISSUES_DIR = ROOT / "issues"

FEATURE_REQUIRED_KEYS = {
    "name", "category", "description", "snippet", "tags",
    "source_bug_id", "tool", "issue_url", "construct_complexity", "ub_type"
}
ALLOWED_FEATURE_KEYS = FEATURE_REQUIRED_KEYS | {"error_pattern"}

TOP_LEVEL_REQUIRED_KEYS = {"tool", "issue_number", "title", "features"}
ALLOWED_TOP_LEVEL_KEYS = {"tool", "issue_number", "title", "features", "skipped_reason", "extraction_summary"}
VALID_CATEGORIES = {"preprocess", "general", "timing", "data_model", "control_flow", "sva_property"}


def validate_feature(feature: dict, index: int, issue_id: str) -> list[str]:
    errors = []
    prefix = f"{issue_id} feature[{index}]"
    
    missing = FEATURE_REQUIRED_KEYS - set(feature.keys())
    if missing:
        errors.append(f"{prefix}: missing keys {missing}")
    
    extra = set(feature.keys()) - ALLOWED_FEATURE_KEYS
    if extra:
        errors.append(f"{prefix}: extra keys {extra}")
    
    if "category" in feature and feature["category"] not in VALID_CATEGORIES:
        errors.append(f"{prefix}: invalid category '{feature.get('category')}'")
    
    if "description" in feature and not feature["description"].startswith("Code should include"):
        errors.append(f"{prefix}: description must start with 'Code should include'")
    
    if "tags" in feature:
        tags = feature["tags"]
        if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
            errors.append(f"{prefix}: tags must be list[str]")
    
    if "construct_complexity" in feature:
        cc = feature["construct_complexity"]
        if not isinstance(cc, int) or not (1 <= cc <= 5):
            errors.append(f"{prefix}: construct_complexity must be int 1-5")
    
    if "snippet" in feature:
        snippet = feature["snippet"]
        if isinstance(snippet, str) and len(snippet) > 600:
            errors.append(f"{prefix}: snippet exceeds 600 chars ({len(snippet)})")
    
    return errors


def validate_issue(issue_id: str, feat_path: Path) -> list[str]:
    errors = []
    prefix = f"{issue_id}"
    
    try:
        data = json.loads(feat_path.read_text())
    except json.JSONDecodeError as e:
        return [f"{prefix}: invalid JSON - {e}"]
    
    if isinstance(data, list):
        errors.append(f"{prefix}: top-level is still a JSON list (must be dict)")
        return errors
    
    if not isinstance(data, dict):
        return [f"{prefix}: top-level is {type(data).__name__} (must be dict)"]
    
    missing = TOP_LEVEL_REQUIRED_KEYS - set(data.keys())
    if missing:
        errors.append(f"{prefix}: top-level missing keys {missing}")
    
    extra = set(data.keys()) - ALLOWED_TOP_LEVEL_KEYS
    if extra:
        errors.append(f"{prefix}: top-level extra keys {extra}")
    
    skipped = data.get("skipped_reason")
    features = data.get("features", [])
    
    if skipped is not None:
        if not isinstance(skipped, str):
            errors.append(f"{prefix}: skipped_reason must be string")
        if features:
            errors.append(f"{prefix}: skipped issue must have empty features list")
    else:
        if not isinstance(features, list):
            errors.append(f"{prefix}: features must be a list")
        else:
            for i, feat in enumerate(features):
                if not isinstance(feat, dict):
                    errors.append(f"{prefix}: feature[{i}] is not a dict")
                    continue
                errors.extend(validate_feature(feat, i, issue_id))
    
    return errors


def main():
    total = 0
    ok = 0
    failed = 0
    all_errors = []
    
    for feat_path in sorted(ISSUES_DIR.rglob("output/features.json")):
        issue_id = feat_path.parent.parent.name
        total += 1
        errors = validate_issue(issue_id, feat_path)
        if errors:
            failed += 1
            all_errors.extend(errors)
        else:
            ok += 1
    
    print(f"Validated {total} features.json files")
    print(f"  OK:     {ok}")
    print(f"  FAILED: {failed}")
    
    if all_errors:
        print(f"\nFirst 30 errors:")
        for err in all_errors[:30]:
            print(f"  - {err}")
        if len(all_errors) > 30:
            print(f"  ... and {len(all_errors) - 30} more errors")
        return 1
    
    print("\nAll files passed validation!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
