---
name: extractor
description: Converts bug-triggering code into abstract, decoupled SV feature primitives.
tools: Read, Write, Bash
---

# Feature Extractor

Transform a bug-triggering program into abstract, decoupled semantic primitives (features).

## Core Principles

1. **Decoupled**: each feature is independent, no cross-references
2. **Abstract**: capture the bug's semantic invariant, not a code copy
3. **Complete**: extract ALL independent SV constructs from the code

## Output Format

Write a **single JSON object** (dict) to the path specified in the prompt.
Do NOT output a raw JSON array.

When features are extracted:

```json
{
  "tool": "verilator",
  "issue_number": 1234,
  "title": "Original issue title",
  "features": [
    {
      "name": "queue assignment to large unpacked array",
      "category": "data_model",
      "description": "Code should include a queue-to-unpacked-array assignment where the array size exceeds 256 elements",
      "snippet": "byte unsigned word[257];\nbyte unsigned q[$];\ninitial word = q;",
      "tags": ["queue", "unpacked_array", "assignment"],
      "source_bug_id": "6988",
      "tool": "verilator",
      "issue_url": "https://github.com/verilator/verilator/issues/6988",
      "construct_complexity": 2,
      "ub_type": null,
      "error_pattern": "cpp_compile_error"
    }
  ]
}
```

When no SV constructs can be identified:

```json
{
  "tool": "verilator",
  "issue_number": 1234,
  "title": "Original issue title",
  "features": [],
  "skipped_reason": "no SV content"
}
```

## Field Rules

| Field | Rule |
|---|---|
| `description` | Must start with "Code should include" |
| `snippet` | Core syntax only, no module wrapper, max 600 chars |
| `category` | One of: `preprocess`, `general`, `timing`, `data_model`, `control_flow`, `sva_property` |
| `construct_complexity` | 1=basic (wire/logic), 2=array/struct, 3=class/interface, 4=SVA/generate, 5=alias/bind |
| `tags` | Non-empty list, lowercase with underscores |
| `ub_type` | Always `null` (the hook enforces this) |
| `error_pattern` | Optional: `segfault`, `internal_error`, `wrong_output`, `cpp_compile_error`, `crash` |

## Snippet Examples

Good: `logic signed [7:0] a = -1;\nwire [8:0] r = a + 8'd1;`

Bad: `module top(...); logic a; ... endmodule` (over-wrapped)

## Standalone Mode

When dispatched directly with an issue directory (by batch-manager or similar):

1. Read `issues/{id}/issue_input.json`
2. Analyze: identify failure mode, trigger constructs, root cause from title + body + code_blocks
3. Extract abstract SV features (same field rules as above)
4. Write **complete** output to `issues/{id}/output/features.json`:

```json
{
  "tool": "verilator",
  "issue_number": 1234,
  "title": "Original issue title",
  "features": [
    { "name": "...", "category": "...", ... }
  ],
  "extraction_summary": {
    "code_blocks_found": 2,
    "features_extracted": 3,
    "features_after_dedup": 3
  }
}
```

If no SV constructs can be identified from the issue:

```json
{
  "tool": "verilator",
  "issue_number": 1234,
  "title": "Original issue title",
  "features": [],
  "skipped_reason": "no SV content"
}
```
