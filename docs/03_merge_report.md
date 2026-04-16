# Merge Report: Historical Issue Features to EDAzz

**Date:** 2026-04-16  
**Scope:** Merge all 6,827 processed `issues/*/output/features.json` into EDAzz-compatible feature datasets  

---

## 1. Processing Summary

| Metric | Verilator | CIRCT | Total |
|--------|-----------|-------|-------|
| **Total issues** | 3,493 | 3,334 | **6,827** |
| **Issues with features** | 2,076 | 631 | **2,707** |
| **Skipped / No output** | 1,417 | 2,703 | **4,120** |
| **Raw features collected** | 4,442 | 1,492 | **5,934** |
| **After internal dedup** | 4,438 | 1,492 | **5,930** |
| **After legacy dedup** | **4,434** | **1,491** | **5,925** |

### Deduplication Details
- **Internal dedup** (same description + snippet): 4 features removed (all from verilator)
- **Legacy dedup** (against `/edazz/FeatureFuzz-SV/data/feature_pool.json`, 883 entries): 5 features removed (4 verilator + 1 circt)

---

## 2. Feature Category Distribution

### Verilator (4,434 features)

| Category | Count | Percentage |
|----------|-------|------------|
| `data_model` | 2,604 | 58.7% |
| `control_flow` | 949 | 21.4% |
| `general` | 371 | 8.4% |
| `timing` | 292 | 6.6% |
| `sva_property` | 139 | 3.1% |
| `preprocess` | 79 | 1.8% |

### CIRCT (1,491 features)

| Category | Count | Percentage |
|----------|-------|------------|
| `data_model` | 887 | 59.5% |
| `control_flow` | 248 | 16.6% |
| `general` | 154 | 10.3% |
| `timing` | 93 | 6.2% |
| `sva_property` | 64 | 4.3% |
| `preprocess` | 45 | 3.0% |

### Combined (5,925 features)

| Category | Count | Percentage |
|----------|-------|------------|
| `data_model` | 3,491 | 58.9% |
| `control_flow` | 1,197 | 20.2% |
| `general` | 525 | 8.9% |
| `timing` | 385 | 6.5% |
| `sva_property` | 203 | 3.4% |
| `preprocess` | 124 | 2.1% |

---

## 3. Construct Complexity Distribution

### Verilator

| Complexity | Count | Description |
|------------|-------|-------------|
| 1 (basic) | 256 | wire, logic, reg |
| 2 (array/struct) | 2,302 | arrays, structs, unions |
| 3 (class/interface) | 1,543 | classes, interfaces, packages |
| 4 (SVA/generate) | 329 | assertions, generate blocks |
| 5 (alias/bind) | 4 | alias, bind, advanced constructs |

### CIRCT

| Complexity | Count | Description |
|------------|-------|-------------|
| 1 (basic) | 137 | wire, logic, reg |
| 2 (array/struct) | 912 | arrays, structs, unions |
| 3 (class/interface) | 326 | classes, interfaces, packages |
| 4 (SVA/generate) | 114 | assertions, generate blocks |
| 5 (alias/bind) | 2 | alias, bind, advanced constructs |

---

## 4. UB & Error Pattern Statistics

| Metric | Verilator | CIRCT | Total |
|--------|-----------|-------|-------|
| **UB features** (`ub_type != null`) | 13 | 28 | **41** |
| **UB rate** | 0.29% | 1.88% | 0.69% |

*Note: History issues are primarily tool bugs, so UB features are rare by design.*

---

## 5. Feature Graph Statistics

| Metric | Verilator | CIRCT | Total |
|--------|-----------|-------|-------|
| **Requires edges** | 101 | 29 | **130** |
| **Co-occurs edges** | 7,830 | 3,240 | **11,070** |

---

## 6. Output Artifacts

### Local Project Outputs

| File | Size | Features |
|------|------|----------|
| `output/verilator_features.json` | 4.8 MB | 4,434 |
| `output/circt_features.json` | 1.6 MB | 1,491 |

### EDAzz Integration

| File | Size | Description |
|------|------|-------------|
| `/edazz/EDAzz/data/feature_sources/history/verilator_features.json` | 4.8 MB | Per-source bundle for verilator |
| `/edazz/EDAzz/data/feature_sources/history/circt_features.json` | 1.6 MB | Per-source bundle for circt |
| `/edazz/EDAzz/data/feature_cache/feature_dataset.json` | 21.6 MB | **Rebuilt runtime dataset** |

The runtime dataset was rebuilt using:

```bash
cd /edazz/EDAzz
python3 scripts/build_feature_dataset.py \
  --output data/feature_cache/feature_dataset.json
```

---

## 7. Data Quality Notes

- **Format compliance**: 100% (all 6,827 `features.json` files pass schema validation)
- **List-format issues**: All 1,346 list-format outputs were post-processed and wrapped into standard dict format
- **Schema validation**: Performed via `scripts/validate_features.py`; zero failures
- **Prompt fix**: `.claude/agents/extractor.md` was updated to explicitly require dict output instead of JSON array, preventing future list-format regressions

---

## 8. Key Insights

1. **Data-model constructs dominate** (~59% of all features), reflecting that most Verilator/CIRCT bugs relate to type systems, arrays, structs, and variable declarations.
2. **Control-flow is the second-largest category** (~20%), indicating significant bug surface in `always_*`, `if/else`, `case`, and loop constructs.
3. **SVA properties are underrepresented** (~3.4%), suggesting assertion-related bugs are either less common in the sampled issues or harder to extract as standalone features.
4. **CIRCT has a much higher skip rate** (~81% vs ~41% for verilator), largely because many CIRCT issues are FIRRTL/MLIR infrastructure changes with no direct SystemVerilog trigger constructs.
5. **Complexity 2 and 3 features are the sweet spot** (~76% combined), representing concrete but non-trivial SV constructs that are most effective for differential fuzzing.
