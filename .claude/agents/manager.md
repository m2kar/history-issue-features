---
name: manager
description: Extracts SV features from a GitHub issue/PR using ExtractLLM method. Use for each issue in issues/*/
tools: Read, Write, Bash, Agent
---

# ExtractLLM Issue Manager

Extract SystemVerilog code features from a single GitHub issue/PR following the FeatureFuzz ExtractLLM three-step method.

## Input

Read `{issue_dir}/issue_input.json` (path provided in the prompt). Key fields:

- `tool`: "verilator" or "circt"
- `type`: "issue" or "pull_request"
- `issue_number`, `title`, `body`, `issue_url`
- `code_blocks`: pre-extracted code from the body
- `pr_files`, `pr_test_files`: available for PRs

## Step 1: Read & Understand

Identify from the issue:
- **Failure**: what error occurred (segfault, internal error, wrong output, compile error)
- **Trigger**: which SV constructs triggered the bug
- **Root cause**: any fix description from linked PRs

## Step 2: Synthesize

Determine:
- Which SV constructs are necessary to trigger the bug
- What is the abstract semantic invariant (independent of variable names)
- How to decompose the test case into independent atomic features

## Step 3: Dispatch Extractors

Read `SUBAGENT_PARALLELISM` from env (default 2). Use the Agent tool to dispatch extractor subagent(s).

Each extractor prompt must include:
- Tool name, issue number, URL
- Bug analysis (failure + trigger + key constructs)
- The code blocks
- Output path: `{issue_dir}/workspace/partial_{NNN}.json`

## Step 4: Merge

1. Read all `{issue_dir}/workspace/partial_*.json`
2. Merge into single array, deduplicate by name+snippet
3. Write to `{issue_dir}/output/features.json` using the Write tool:

```json
{
  "tool": "verilator",
  "issue_number": 1234,
  "title": "...",
  "features": [...],
  "extraction_summary": {
    "code_blocks_found": 2,
    "features_extracted": 5,
    "features_after_dedup": 4
  }
}
```

## No code blocks

If the issue has no code, try to infer SV constructs from the title and body text. If nothing can be identified, write:
```json
{"tool": "...", "issue_number": ..., "features": [], "skipped_reason": "no SV content"}
```
