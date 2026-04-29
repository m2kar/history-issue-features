# Feature Dataset Statistics Report

**Generated:** 2026-04-21
**Source files:** `output/{verilator,circt,iverilog,yosys}_features.json`

---

## 1. Overall Summary

| Tool      | Features | Share   |
|-----------|----------|---------|
| verilator | 4434     | 48.94%  |
| circt     | 1491     | 16.46%  |
| iverilog  | 938      | 10.35%  |
| yosys     | 2197     | 24.25%  |
| **Total** | 9060     | 100.00% |

- **Unique `feature_id`s:** 9060 (100.00% of total rows)
- **Duplicate `feature_id` rows (cross-tool):** 0 (collapsed from 0 IDs)
- **Unique `(description, snippet)` signatures:** 9060

## 2. Category Distribution

| Category     | verilator | circt | iverilog | yosys | Total | Share   |
|--------------|-----------|-------|----------|-------|-------|---------|
| data_model   | 2604      | 887   | 587      | 1210  | 5288  | 58.37%  |
| control_flow | 949       | 248   | 168      | 427   | 1792  | 19.78%  |
| general      | 371       | 154   | 48       | 241   | 814   | 8.98%   |
| timing       | 292       | 93    | 89       | 198   | 672   | 7.42%   |
| sva_property | 139       | 64    | 10       | 62    | 275   | 3.04%   |
| preprocess   | 79        | 45    | 36       | 59    | 219   | 2.42%   |
| **Total**    | 4434      | 1491  | 938      | 2197  | 9060  | 100.00% |

## 3. Top Tags (Top 30 per tool, union)

- **Distinct tags (global):** 7175
- **Avg tags per feature:** 4.86

| Rank | Tag                  | Global | verilator | circt | iverilog | yosys |
|------|----------------------|--------|-----------|-------|----------|-------|
| 1    | data_model           | 5288   | 2604      | 887   | 587      | 1210  |
| 2    | control_flow         | 1792   | 949       | 248   | 168      | 427   |
| 3    | general              | 814    | 371       | 154   | 48       | 241   |
| 4    | timing               | 687    | 301       | 95    | 92       | 199   |
| 5    | unpacked_array       | 633    | 377       | 71    | 81       | 104   |
| 6    | parameter            | 407    | 251       | 15    | 39       | 102   |
| 7    | class                | 385    | 284       | 20    | 81       | 0     |
| 8    | interface            | 375    | 319       | 21    | 9        | 26    |
| 9    | assignment           | 338    | 189       | 60    | 48       | 41    |
| 10   | concatenation        | 322    | 143       | 47    | 25       | 107   |
| 11   | wire                 | 318    | 77        | 124   | 41       | 76    |
| 12   | sva_property         | 275    | 139       | 64    | 10       | 62    |
| 13   | typedef              | 259    | 193       | 19    | 27       | 20    |
| 14   | struct               | 244    | 151       | 66    | 17       | 10    |
| 15   | for_loop             | 226    | 122       | 14    | 30       | 60    |
| 16   | memory               | 221    | 14        | 67    | 2        | 138   |
| 17   | signed               | 220    | 69        | 41    | 40       | 70    |
| 18   | preprocess           | 219    | 79        | 45    | 36       | 59    |
| 19   | module_instantiation | 215    | 93        | 25    | 22       | 75    |
| 20   | localparam           | 203    | 145       | 3     | 23       | 32    |
| 21   | function             | 201    | 125       | 9     | 32       | 35    |
| 22   | generate             | 193    | 114       | 8     | 28       | 43    |
| 23   | ternary              | 186    | 61        | 22    | 27       | 76    |
| 24   | always_comb          | 181    | 98        | 32    | 26       | 25    |
| 25   | always_block         | 180    | 73        | 32    | 19       | 56    |
| 26   | always_ff            | 173    | 73        | 50    | 5        | 45    |
| 27   | enum                 | 162    | 99        | 19    | 33       | 11    |
| 28   | register             | 161    | 12        | 75    | 5        | 69    |
| 29   | task                 | 156    | 105       | 11    | 19       | 21    |
| 30   | queue                | 154    | 124       | 4     | 26       | 0     |

## 4. Construct Complexity

| Tool      | cc=1 | cc=2 | cc=3 | cc=4 | cc=5 | missing | mean | median |
|-----------|------|------|------|------|------|---------|------|--------|
| verilator | 256  | 2302 | 1543 | 329  | 4    | 0       | 2.44 | 2.0    |
| circt     | 137  | 912  | 326  | 114  | 2    | 0       | 2.28 | 2      |
| iverilog  | 88   | 580  | 220  | 50   | 0    | 0       | 2.25 | 2.0    |
| yosys     | 212  | 1389 | 446  | 139  | 11   | 0       | 2.25 | 2      |
| **Total** | 693  | 5183 | 2535 | 632  | 17   | 0       | 2.35 | 2.0    |

## 5. UB Type Distribution

| ub_type | count | share   |
|---------|-------|---------|
| (null)  | 9060  | 100.00% |

## 6. Error Pattern Distribution

- **Distinct error patterns:** 151

### Top 25 error patterns

| error_pattern           | verilator | circt | iverilog | yosys | Total | Share  |
|-------------------------|-----------|-------|----------|-------|-------|--------|
| wrong_output            | 1780      | 785   | 418      | 1047  | 4030  | 44.48% |
| (null)                  | 514       | 345   | 110      | 581   | 1550  | 17.11% |
| internal_error          | 821       | 204   | 99       | 194   | 1318  | 14.55% |
| cpp_compile_error       | 767       | 20    | 37       | 15    | 839   | 9.26%  |
| crash                   | 68        | 78    | 95       | 89    | 330   | 3.64%  |
| syntax_error            | 98        | 1     | 60       | 50    | 209   | 2.31%  |
| segfault                | 89        | 19    | 21       | 68    | 197   | 2.17%  |
| unsupported             | 136       | 0     | 0        | 3     | 139   | 1.53%  |
| hang                    | 30        | 4     | 10       | 14    | 58    | 0.64%  |
| parse_error             | 3         | 0     | 7        | 13    | 23    | 0.25%  |
| missing_warning         | 13        | 0     | 3        | 0     | 16    | 0.18%  |
| infinite_loop           | 4         | 0     | 3        | 6     | 13    | 0.14%  |
| parser_error            | 0         | 1     | 6        | 6     | 13    | 0.14%  |
| performance_degradation | 3         | 0     | 0        | 7     | 10    | 0.11%  |
| unsupported_error       | 9         | 0     | 0        | 0     | 9     | 0.10%  |
| elaboration_error       | 0         | 0     | 8        | 1     | 9     | 0.10%  |
| syntax error            | 4         | 0     | 3        | 1     | 8     | 0.09%  |
| unsupported_feature     | 2         | 0     | 3        | 3     | 8     | 0.09%  |
| timeout                 | 0         | 3     | 0        | 5     | 8     | 0.09%  |
| assert                  | 0         | 0     | 7        | 1     | 8     | 0.09%  |
| warning                 | 2         | 0     | 3        | 2     | 7     | 0.08%  |
| assertion_failure       | 0         | 0     | 5        | 2     | 7     | 0.08%  |
| performance_issue       | 2         | 0     | 0        | 4     | 6     | 0.07%  |
| unknown_format_code     | 6         | 0     | 0        | 0     | 6     | 0.07%  |
| lint_error              | 1         | 5     | 0        | 0     | 6     | 0.07%  |
| _other (126 patterns)_  | 82        | 26    | 40       | 85    | 233   | 2.57%  |

## 7. Snippet Length (characters / lines)

| Tool      | char min | char max | char mean | char median | line min | line max | line mean | line median |
|-----------|----------|----------|-----------|-------------|----------|----------|-----------|-------------|
| verilator | 5        | 545      | 99.26     | 83.0        | 1        | 22       | 3.96      | 3.0         |
| circt     | 6        | 578      | 98.16     | 80          | 1        | 23       | 3.84      | 3           |
| iverilog  | 2        | 577      | 83.41     | 68.0        | 1        | 17       | 3.69      | 3.0         |
| yosys     | 6        | 551      | 93.9      | 80          | 1        | 21       | 3.67      | 3           |
| **Total** | 2        | 578      | 96.14     | 80.0        | 1        | 23       | 3.84      | 3.0         |

## 8. Features per Source Issue

| Tool      | issues | features | min | max | mean | median |
|-----------|--------|----------|-----|-----|------|--------|
| verilator | 2058   | 4434     | 1   | 12  | 2.15 | 2.0    |
| circt     | 630    | 1491     | 1   | 10  | 2.37 | 2.0    |
| iverilog  | 486    | 938      | 1   | 6   | 1.93 | 2.0    |
| yosys     | 1024   | 2197     | 1   | 10  | 2.15 | 2.0    |
| **Total** | 4194   | 9060     | 1   | 12  | 2.16 | 2.0    |

### 8.1 Top-20 Issues by Feature Count

| Rank | tool      | source_bug_id  | features | url                                                 |
|------|-----------|----------------|----------|-----------------------------------------------------|
| 1    | verilator | verilator-6744 | 12       | https://github.com/verilator/verilator/issues/6744  |
| 2    | circt     | circt-10033    | 10       | https://github.com/llvm/circt/pull/10033            |
| 3    | yosys     | 4486           | 10       | https://github.com/YosysHQ/yosys/issues/4486        |
| 4    | circt     | circt-10028    | 9        | https://github.com/llvm/circt/issues/10028          |
| 5    | circt     | circt-10049    | 9        | https://github.com/llvm/circt/issues/10049          |
| 6    | circt     | circt-18       | 9        | https://github.com/llvm/circt/issues/18             |
| 7    | verilator | 1004           | 8        | https://github.com/verilator/verilator/issues/1004  |
| 8    | circt     | circt-10014    | 8        | https://github.com/llvm/circt/pull/10014            |
| 9    | circt     | circt-10071    | 8        | https://github.com/llvm/circt/pull/10071            |
| 10   | circt     | circt-7414     | 8        | https://github.com/llvm/circt/issues/7414           |
| 11   | verilator | 2322           | 7        | https://github.com/verilator/verilator/pull/2322    |
| 12   | verilator | 3984           | 7        | https://github.com/verilator/verilator/issues/3984  |
| 13   | verilator | 7050           | 7        | https://github.com/verilator/verilator/pull/7054    |
| 14   | verilator | 7100           | 7        | https://github.com/verilator/verilator/pull/7100    |
| 15   | verilator | 7310           | 7        | https://github.com/verilator/verilator/pull/7310    |
| 16   | circt     | circt-543      | 7        | https://github.com/llvm/circt/issues/543            |
| 17   | circt     | circt-9480     | 7        | https://github.com/llvm/circt/pull/9480             |
| 18   | yosys     | 4987           | 7        | https://github.com/YosysHQ/yosys/issues/4987        |
| 19   | verilator | 1005           | 6        | https://github.com/steveicarus/iverilog/issues/1005 |
| 20   | verilator | 2332           | 6        | https://github.com/verilator/verilator/pull/2332    |

## 9. Description Length (characters)

| Tool      | min | max | mean   | median |
|-----------|-----|-----|--------|--------|
| verilator | 52  | 427 | 126.64 | 122.0  |
| circt     | 57  | 292 | 135.41 | 130    |
| iverilog  | 58  | 299 | 128.76 | 124.0  |
| yosys     | 60  | 412 | 143.42 | 136    |
| **Total** | 52  | 427 | 132.37 | 126.0  |

## 10. Description Format Compliance

Project requires every description to begin with `Code should include`.

| Tool      | compliant | non-compliant | compliance rate |
|-----------|-----------|---------------|-----------------|
| verilator | 4434      | 0             | 100.00%         |
| circt     | 1491      | 0             | 100.00%         |
| iverilog  | 938       | 0             | 100.00%         |
| yosys     | 2197      | 0             | 100.00%         |
| **Total** | 9060      | 0             | 100.00%         |

## 11. Cross-tool Overlap

- **Features appearing in multiple tools:** 0

## 12. Feature Name Uniqueness

| Tool      | features | unique names | collisions |
|-----------|----------|--------------|------------|
| verilator | 4434     | 4406         | 28         |
| circt     | 1491     | 1486         | 5          |
| iverilog  | 938      | 936          | 2          |
| yosys     | 2197     | 2190         | 7          |
| **Total** | 9060     | 8999         | 61         |

## 13. Issue Coverage vs Raw Corpus

| Tool      | raw issues | issues w/ features | coverage |
|-----------|------------|--------------------|----------|
| verilator | 6812       | 2058               | 30.21%   |
| circt     | 10185      | 630                | 6.19%    |
| iverilog  | 1221       | 486                | 39.80%   |
| yosys     | 5381       | 1024               | 19.03%   |

---

_Generated by `scripts/analyze_dataset.py`._
