#!/usr/bin/env python3
"""PreToolUse hook: validate and normalize feature output before writing.

Validates schema, forces ub_type/ub_quote to null, and rewrites content
so agents don't need to worry about UB fields at all.
"""
import json
import sys

try:
    event = json.load(sys.stdin)
except Exception:
    sys.exit(0)

if event.get("tool_name") != "Write":
    sys.exit(0)

tool_input = event.get("tool_input", {})
path = tool_input.get("file_path", "")

# Only validate feature/partial JSON files
if not (path.endswith(".json") and ("features" in path or "partial" in path)):
    sys.exit(0)

content = tool_input.get("content", "")


def deny(reason):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)


try:
    data = json.loads(content)
except json.JSONDecodeError as e:
    deny(f"Invalid JSON: {e}")

# Two formats: {"features": [...]} or [...]
if isinstance(data, dict):
    if "features" not in data:
        sys.exit(0)
    features = data["features"]
elif isinstance(data, list):
    features = data
else:
    sys.exit(0)

if not isinstance(features, list):
    deny("'features' must be a JSON array")

VALID_CATEGORIES = {"preprocess", "timing", "control_flow", "data_model", "general", "sva_property"}
VALID_TOOLS = {"verilator", "circt", "iverilog", "yosys"}

modified = False

for i, feat in enumerate(features):
    # Required fields
    required = [
        "name", "category", "description", "snippet", "tags",
        "source_bug_id", "tool", "issue_url", "construct_complexity",
    ]
    missing = [k for k in required if k not in feat]
    if missing:
        deny(f"Feature [{i}] '{feat.get('name', '?')}' missing fields: {missing}")

    # description prefix
    if not feat["description"].startswith("Code should include"):
        deny(f"Feature [{i}] description must start with 'Code should include'. "
             f"Got: '{feat['description'][:50]}...'")

    # category
    if feat["category"] not in VALID_CATEGORIES:
        deny(f"Feature [{i}] invalid category '{feat['category']}'. "
             f"Must be: {sorted(VALID_CATEGORIES)}")

    # snippet non-empty
    if not feat["snippet"].strip():
        deny(f"Feature [{i}] '{feat['name']}' has empty snippet")

    # tags non-empty list
    if not isinstance(feat["tags"], list) or not feat["tags"]:
        deny(f"Feature [{i}] tags must be non-empty list")

    # construct_complexity range
    c = feat["construct_complexity"]
    if not isinstance(c, int) or c < 1 or c > 5:
        deny(f"Feature [{i}] construct_complexity must be integer 1-5, got {c}")

    # tool
    if feat["tool"] not in VALID_TOOLS:
        deny(f"Feature [{i}] tool must be one of {sorted(VALID_TOOLS)}, got '{feat['tool']}'")

    # source_bug_id
    if not isinstance(feat["source_bug_id"], str) or not feat["source_bug_id"]:
        deny(f"Feature [{i}] source_bug_id must be non-empty string")

    # snippet length
    if len(feat["snippet"]) > 600:
        deny(f"Feature [{i}] snippet too long ({len(feat['snippet'])} chars, max 600).")

    # name length
    if len(feat["name"]) > 120:
        deny(f"Feature [{i}] name too long ({len(feat['name'])} chars, max 120)")

    # Force ub_type and ub_quote to null (these are language-level UB from IEEE 1800,
    # not tool bugs — history issues are tool bugs, so always null)
    if feat.get("ub_type") is not None:
        feat["ub_type"] = None
        modified = True
    if feat.get("ub_quote") is not None:
        feat["ub_quote"] = None
        modified = True

# If we modified any fields, rewrite the content
if modified:
    new_content = json.dumps(data, indent=2, ensure_ascii=False)
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "updatedInput": {
                "file_path": path,
                "content": new_content,
            },
        }
    }))
    sys.exit(0)

sys.exit(0)
