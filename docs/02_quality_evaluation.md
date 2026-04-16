# Quality Evaluation: Feature Extraction from Historical Issues

**Date:** 2026-04-14  
**Scope:** Random sampling of 10 completed issues from `issues/*/output/features.json`  
**Evaluator:** Automated agent review + manual analysis  

---

## 1. Sampling Method

From **2,478** issues that already have `features.json`, we randomly sampled **10 issues** (`seed=42`) to evaluate extraction quality.

| # | Issue | Status |
|---|-------|--------|
| 1 | `circt-10057` | 6 features |
| 2 | `circt-10014` | 8 features |
| 3 | `circt-4257` | 1 feature |
| 4 | `circt-3170` | skipped |
| 5 | `verilator-3824` | 2 features |
| 6 | `verilator-4366` | 1 feature |
| 7 | `verilator-384` | 1 feature |
| 8 | `verilator-4289` | skipped |
| 9 | `verilator-3945` | 1 feature |
| 10 | `verilator-4016` | 2 features |

Evaluation dimensions (1–5 scale):

- **Relevance**: Are the extracted features related to the actual bug/defect?
- **Accuracy**: Do the features correctly describe the bug-triggering SV construct?
- **Abstraction**: Are the features decoupled, independent, and reusable primitives?
- **Completeness**: Are critical triggering constructs missing?
- **Skip Reasoning** (if applicable): Is the skip decision justified?

---

## 2. Format-Compliance Issues (Critical)

Before content evaluation, a **severe format problem** was found:

| Format | Count | Note |
|--------|-------|------|
| **Dict format (required)** | 2,205 | Correct: contains `tool`, `issue_number`, `title`, `features` / `skipped_reason` |
| **List format (wrong)** | **273** | **11.0%** of all outputs are raw JSON lists instead of the required dict wrapper |
| Invalid / unreadable | 0 | — |

**Impact:** List-format outputs will break downstream `merge.py` and EDAzz ingestion pipelines.

**Root cause:** In batch mode, the `extractor` subagent sometimes emits a raw feature list and forgets to wrap it in the required dict schema. This happens most frequently in recent `verilator-46xx` batches.

**Immediate action required:** Add a schema-validation / auto-wrap step before marking an issue as "done."

---

## 3. Per-Issue Assessment

### 3.1 circt-10057 — `$monitor` system-task implementation

| Dimension | Score | Comment |
|-----------|-------|---------|
| Relevance | 5 | The 6 features map 1-to-1 to the PR's goal of supporting `$monitor*` |
| Accuracy | 5 | Correctly covers `$monitor`, `$monitorb`, `$monitoro`, `$monitorh`, `$monitoron`, `$monitoroff` |
| Abstraction | 4 | Each variant is split into its own feature; acceptable, but could be merged into a parameterized `$monitor*` family to reduce redundancy |
| Completeness | 4 | All variants are covered, but the semantic rule "only the last monitor task is active" is not captured |
| **Average** | **4.5** | Accurate extraction for an implementation PR; merge strategy could be refined. |

---

### 3.2 circt-10014 — `FileLineColRange` metadata support ⚠️

| Dimension | Score | Comment |
|-----------|-------|---------|
| Relevance | 2 | The PR is an internal compiler infrastructure change; it has **no causal relationship** with specific SV constructs |
| Accuracy | 2 | The 8 extracted features (multi-line always/if-else/module/always_comb/case/struct/generate/single assign) are generic constructs present in any code |
| Abstraction | 3 | The constructs themselves are abstract, but the extraction is fundamentally off-target |
| Completeness | 1 | Fails to address the PR core: source-range capture in `ImportVerilog` |
| **Average** | **2.0** | **Severe mis-extraction**. Infrastructure/meta-data PRs should be skipped instead of forcing unrelated SV features. |

---

### 3.3 circt-4257 — unnecessary `begin/end` in ExportVerilog

| Dimension | Score | Comment |
|-----------|-------|---------|
| Relevance | 4 | Directly related to the inlined-assignment triggering scenario |
| Accuracy | 4 | Translates MLIR `sv.initial` + `sv.logic` + `sv.bpassign` into `initial automatic logic foo = 1'b1;` fairly well |
| Abstraction | 4 | Describes the abstract pattern "initial block with single inlined logic variable assignment" |
| Completeness | 4 | Captures the core bug trigger |
| **Average** | **4.0** | Solid extraction. |

---

### 3.4 circt-3170 — flattening struct types

| Dimension | Score | Comment |
|-----------|-------|---------|
| Skip Reasoning | 4 | `skipped_reason: "no SV content"` is accurate. The PR revolves around MLIR HW dialect (`hw.struct_create`, etc.) |
| **Average** | **4.0** | Reasonable skip. A more precise reason would be "MLIR infrastructure change, no SV trigger construct," but the current label is sufficient. |

---

### 3.5 verilator-3824 — Bit OR tree misoptimization

| Dimension | Score | Comment |
|-----------|-------|---------|
| Relevance | 5 | Both features map directly to the misoptimization trigger path |
| Accuracy | 5 | Precisely reproduces `(|A) | C` and `{1'h0, A}` + `B[6]` from the original issue |
| Abstraction | 4 | The first feature name is long and embeds issue-specific variable relationships (`concat_index`), but the pattern is still reusable |
| Completeness | 4 | Covers reduction OR, bitwise OR, concat, bit-index, and unary NOT |
| **Average** | **4.5** | High-quality extraction of a complex constant-propagation + bit-tree interaction. |

---

### 3.6 verilator-4366 — `super.new` handling

| Dimension | Score | Comment |
|-----------|-------|---------|
| Relevance | 5 | Directly tied to `super.new` in class constructors |
| Accuracy | 5 | Snippet exactly shows `super.new(a)` followed by a conditional `return` inside a derived-class constructor |
| Abstraction | 4 | The description is abstract, but the snippet retains example-specific `a < 10` |
| Completeness | 5 | One feature captures the sufficient-and-necessary condition for the bug |
| **Average** | **4.75** | **Excellent**. Highly focused and accurate. |

---

### 3.7 verilator-384 — unpacked array VCD boundary (>32 elements)

| Dimension | Score | Comment |
|-----------|-------|---------|
| Relevance | 5 | Directly matches the unpacked-array VCD-generation boundary issue |
| Accuracy | 4 | `addr_t a_addr[33-1:0];` is accurate, but the description makes "33 elements" a core condition rather than a generic boundary test |
| Abstraction | 3 | Overly bound to concrete numbers (33) and variable names (`addr_t`, `a_addr`). The primitive should be "unpacked array with more than 32 elements" |
| Completeness | 4 | Catches the main trigger, but misses the contrast with the 32-element baseline |
| **Average** | **4.0** | Relevant and accurate, but poor abstraction. Concrete values should stay in `snippet`, not in `description`. |

---

### 3.8 verilator-4289 — performance tuning question

| Dimension | Score | Comment |
|-----------|-------|---------|
| Skip Reasoning | 5 | Pure performance-consultation / user-support issue with no SV bug trigger |
| **Average** | **5.0** | Perfect skip decision. |

---

### 3.9 verilator-3945 — const string func

| Dimension | Score | Comment |
|-----------|-------|---------|
| Relevance | 5 | Directly related to string handling in constant functions |
| Accuracy | 4 | Shows `return "FOO"`, but the issue says "String assignments aren't working in constant functions" more broadly. The `error_pattern: internal_error` label is also imprecise |
| Abstraction | 4 | "string constant assignment in constant function" is reasonably abstract |
| Completeness | 3 | Only covers `return string_literal`; misses non-return string assignments inside constant functions |
| **Average** | **4.0** | Basically correct but incomplete. Should broaden from "return string" to "string assignment in constant function." |

---

### 3.10 verilator-4016 — `default disable iff`

| Dimension | Score | Comment |
|-----------|-------|---------|
| Relevance | 5 | `default disable iff` is the core SVA construct requested |
| Accuracy | 5 | Snippet precisely shows `default disable iff (!rst_n);` and a `default clocking` block |
| Abstraction | 5 | Both `default disable iff` and `default clocking` are standard, independent, reusable SVA primitives |
| Completeness | 4 | Core construct is covered. `default clocking` is present in the example but is a secondary extra feature |
| **Average** | **4.75** | High-quality extraction with strong abstraction. |

---

## 4. Overall Content Score

| Issue | Average Score |
|-------|---------------|
| circt-10057 | 4.5 |
| circt-10014 | 2.0 |
| circt-4257 | 4.0 |
| circt-3170 | 4.0 (Skip) |
| verilator-3824 | 4.5 |
| verilator-4366 | 4.75 |
| verilator-384 | 4.0 |
| verilator-4289 | 5.0 (Skip) |
| verilator-3945 | 4.0 |
| verilator-4016 | 4.75 |

**Overall average (10 samples):** **4.15 / 5.0**  
**Excluding the outlier `circt-10014`:** **4.53 / 5.0**

---

## 5. Common Problems

### 5.1 Format non-compliance (critical)
- **273 files (11%)** are raw JSON lists instead of the required dict wrapper. This breaks downstream pipelines and must be fixed immediately.

### 5.2 Mis-extraction of infrastructure changes
- `circt-10014` is the clearest example: a compiler-internal metadata / source-range refactor was forced into 8 unrelated SV features. The current logic cannot distinguish "infrastructure / meta-data / refactoring" PRs from true bug-triggering constructs.

### 5.3 Inconsistent abstraction discipline
- Some features embed concrete constants (`33 elements`), variable names (`a_addr`), or specific bit-widths (`1'h0`) into `description` or `name`. These should remain in `snippet` only; the description must stay at the construct-category level.

### 5.4 `error_pattern` lacks a unified taxonomy
- `verilator-3945` was labeled `internal_error`, but the actual behavior is a semantic / compile-time failure. Without a clear classification guide, this field becomes noisy.

### 5.5 Over-splitting of variant families
- `circt-10057` created 6 separate features for `$monitor*` format variants. While accurate, it inflates the dataset. Such families are better represented as one feature with variant tags.

---

## 6. Actionable Recommendations

### 6.1 Fix format compliance immediately
1. **Post-process all existing outputs:** Detect list-format `features.json` and auto-wrap them into the required dict schema.
2. **Harden the extractor prompt:** Append an explicit reminder: *"You MUST output a single JSON **dict** with keys `tool`, `issue_number`, `title`, and either `features` (list) or `skipped_reason` (string). Do NOT output a raw JSON list."*
3. **Add CI/schema check:** Before marking an issue "done," validate with `jsonschema`.

### 6.2 Improve skip detection for non-bug content
Add heuristics (title + body keyword matching + absence of code blocks) to auto-skip:
- Keywords: `source range`, `metadata`, `refactor`, `FileLineCol`, `generalization`, `infrastructure`, `CI`, `lint warning`
- Condition: **no** code blocks AND keywords present → high-confidence skip.

### 6.3 Enforce abstraction rules in post-processing
Add a lint step that flags features whose `name` or `description` contains:
- Specific numeric literals (`33`, `64`)
- Issue-specific variable names (`a_addr`, `foo_func`)
- Concrete bit-width constants in descriptions (`1'h0`)

Flagged items should be rewritten to generalize the construct.

### 6.4 Define `error_pattern` taxonomy
Adopt a strict 4-class scheme:

| Label | Meaning |
|-------|---------|
| `syntax_error` | Parser rejects the input |
| `compilation_error` | Semantic / type-check failure (post-parse, pre-simulation) |
| `internal_error` | Tool crash, assertion failure, or ICE |
| `wrong_output` | Simulation output or generated code is incorrect |

### 6.5 Merge variant families
For system-task format variants (`$display`/`$displayb`/`$monitor`/`$monitorb`, etc.), prefer one feature with a description like:

> "Code should include a `$monitor` system task (any of `$monitor`, `$monitorb`, `$monitoro`, `$monitorh`)"

Use `tags` to record the specific variant if needed.

---

## 7. Summary

- **Content quality is generally good** (≈4.5/5 when excluding clear outliers).
- **Skip decisions are mostly correct** for Q&A and infrastructure issues.
- **The dominant quality risk is format compliance**: 11% of outputs are JSON lists instead of dicts, which will corrupt downstream merging.
- **The second risk is mis-extraction of infrastructure PRs**, where the agent forces generic SV features onto compiler-internal changes.

**Priority order:**
1. Fix list-format outputs and add schema guards.
2. Improve infrastructure/skip heuristics.
3. Refine abstraction lints and `error_pattern` taxonomy.
