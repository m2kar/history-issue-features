# Design: History Issue Feature Extraction

从 Verilator/CIRCT 历史 GitHub Issue/PR 中提取 SystemVerilog 代码特征，
用于 EDAzz 差分 fuzzing 工具的特征库。

## 1. 目标

- 从 GitHub 爬取 Verilator/CIRCT 的 issue/PR 原始数据
- 按 FeatureFuzz 论文的 ExtractLLM 三步法提取 SV 代码特征
- 输出符合 EDAzz `validate_feature_dataset()` 严格约束的数据集

## 2. 方法论

采用 FeatureFuzz 论文的 **ExtractLLM** 三步法：

1. **阅读理解 (Read & Understand)**: 读取 bug report，理解失效现象、触发机制、根本原因
2. **综合分析 (Synthesize)**: 联合分析 bug report + root cause + bug-triggering program，定位关键 SV 构造
3. **抽象提取 (Abstract & Extract)**: 从具体测试用例转化为**解耦的抽象语义原语** — 每个特征独立、不互相引用、可复用

## 3. 系统架构

```
crawl_issues.py ──→ raw/*.jsonl (GitHub API 原始数据)
                        │
prepare_inputs.py ──→ issues/*/issue_input.json (筛选 + 预处理)
                        │
run-all.py (WorkerPool) │
  └─ run-issue.py ──→ claude --agent manager
                        ├─ Step 1-2: 阅读理解 + 综合分析
                        └─ Step 3: 并行派发 extractor subagent(s)
                              ├─ workspace/partial_001.json
                              └─ workspace/partial_002.json
                        │
                   ──→ issues/*/output/features.json (汇总去重)
                        │
merge.py ──→ output/merged_history_v2_features.json (EDAzz 兼容)
```

## 4. 项目结构

```
/edazz/history-issue-features/
├── CLAUDE.md                              # 项目约束
├── config.yaml                            # 运行配置: providers, 并行度, 超时
├── pyproject.toml                         # Python 3.12+, pyyaml
│
├── .claude/
│   ├── settings.json                      # 权限 + Hook 注册
│   ├── agents/
│   │   ├── manager.md                     # ExtractLLM 三步法编排
│   │   └── extractor.md                   # 抽象语义原语提取
│   └── hooks/
│       ├── validate-feature.py            # PreToolUse: schema 验证 + 强制 ub_type=null
│       └── notify-progress.py             # SubagentStop: 进度日志
│
├── scripts/
│   ├── crawl_issues.py                    # 从 GitHub 爬取原始 issue/PR
│   ├── prepare_inputs.py                  # 筛选 + 预处理
│   └── fetch_pr_details.py               # 按需获取 PR 文件列表
│
├── run-all.py                             # 批量编排器 (WorkerPool, 支持多 provider 并行)
├── run-issue.py                           # 单 issue 执行器
├── merge.py                               # 合并 + 去重 + 图构建 + rarity + EDAzz 输出
│
├── raw/                                   # 原始爬取数据
│   ├── verilator.jsonl                    # 6,812 条 (截至 2026-04-13)
│   ├── circt.jsonl                        # 10,185 条
│   └── crawl_state.json                   # 爬取进度
│
├── issues/                                # 每 issue/PR 工作目录 (6,827 个)
│   └── {tool}-{number}/
│       ├── issue_input.json               # 预处理后的 agent 输入
│       ├── workspace/                     # 中间产物
│       └── output/features.json           # 该 issue 提取的特征
│
├── output/
│   └── merged_history_v2_features.json    # 最终合并输出
│
├── docs/
│   └── 01_design.md                       # 本文件
│
└── logs/
```

## 5. 数据管道

### Stage 0: 爬取 (`scripts/crawl_issues.py`)

- **数据源**: GitHub REST API via `gh` CLI
- **仓库**: `verilator/verilator` (6,812 条), `llvm/circt` (10,185 条)
- **基线**: 复制 `/edazz/mirtl-pocs/issues/` 已有数据，增量爬取新 issue
- **频率控制**: 2,000 requests/hour, 每请求间隔 1.8s, tmux 后台运行
- **输出**: `raw/{tool}.jsonl` (每行 `number\tJSON`)

```bash
# 全量 (首次)
python3 scripts/crawl_issues.py --full

# 增量 (后续)
python3 scripts/crawl_issues.py
```

### Stage 1: 预处理 (`scripts/prepare_inputs.py`)

读取 `raw/*.jsonl`, 筛选有效 issue/PR, 生成 `issues/*/issue_input.json`.

**筛选规则** (不限 state, open/closed 均纳入):

| 工具 | 纳入条件 | 排除条件 |
|------|---------|---------|
| Verilator | body 含代码块或 SV 关键词; PR 含 fix + 代码块 | label: documentation, feature request |
| CIRCT | body 含 .sv/.v 或 circt-verilog 关键词 | 纯 FIRRTL/MLIR, label: documentation |

**质量验证**: 预处理后随机抽样 20 条检查误报/漏报，迭代优化筛选规则。

**issue_input.json 格式**:
```json
{
  "tool": "verilator",
  "type": "issue",
  "issue_number": 6988,
  "issue_url": "https://github.com/verilator/verilator/issues/6988",
  "title": "assigning queue to unpacked array larger than 256...",
  "body": "...",
  "labels": ["new"],
  "state": "closed",
  "created_at": "2026-01-28",
  "code_blocks": ["module top; ..."],
  "pr_files": null,
  "pr_test_files": null
}
```

### Stage 2: ExtractLLM 特征提取

`run-all.py` (WorkerPool) → `run-issue.py` → `claude --agent manager`

Manager agent 执行 ExtractLLM 三步法，派发 extractor subagent 提取特征。

每个 issue 输出 `output/features.json`:
```json
{
  "tool": "verilator",
  "issue_number": 6988,
  "title": "...",
  "features": [...],
  "extraction_summary": {
    "code_blocks_found": 2,
    "features_extracted": 5,
    "features_after_dedup": 4
  }
}
```

### Stage 3: 合并 (`merge.py`)

收集所有 per-issue features → 去重 → 图构建 → rarity 计算 → EDAzz 格式输出。

```bash
python3 merge.py                    # 合并 + 验证
python3 merge.py --stats            # 仅统计
```

## 6. Agent 设计

### 6.1 Manager (`.claude/agents/manager.md`)

| 字段 | 值 |
|------|------|
| tools | Read, Write, Bash, Agent |
| 角色 | ExtractLLM 编排: 读取 issue → 分析 bug → 派发 extractor → 汇总结果 |

**流程**: Read & Understand → Synthesize → Dispatch Extractors → Merge Results

### 6.2 Extractor (`.claude/agents/extractor.md`)

| 字段 | 值 |
|------|------|
| tools | Read, Write |
| 角色 | 将 bug-triggering code 转化为解耦的抽象语义原语 |

**每个特征必须包含**:

| 字段 | 规范 |
|------|------|
| `name` | 简洁名称, ≤120 字符 |
| `category` | preprocess / general / timing / data_model / control_flow / sva_property |
| `description` | 必须以 "Code should include" 开头 |
| `snippet` | 核心语法, 不包 module, ≤600 字符 |
| `tags` | 非空 list, 小写下划线 |
| `source_bug_id` | issue number (string) |
| `tool` | verilator / circt |
| `issue_url` | 完整 GitHub URL |
| `construct_complexity` | 1-5 (1=wire/logic, 5=alias/bind) |
| `ub_type` | 总是 null (由 hook 强制) |

### 6.3 Hook: validate-feature.py

PreToolUse hook, 在 Write 特征 JSON 时触发:

1. **Schema 验证**: 检查必填字段、类型、范围
2. **强制 ub_type=null**: 通过 `updatedInput` 将所有 `ub_type`/`ub_quote` 字段重写为 null
   - 原因: history issues 是工具实现 bug, 不是 IEEE 1800 语言级 UB
   - Agent 不需要关心 UB 字段, hook 自动处理

## 7. 去重策略

### 7.1 项目内去重

normalize(description + snippet) → SHA1 → 相同 hash 保留先出现的

### 7.2 与 legacy 去重

加载 `/edazz/FeatureFuzz-SV/data/feature_pool.json` (891 条), snippet token Jaccard > 0.8 视为重复

### 7.3 同 issue 内去重

Manager 汇总时按 name + snippet 去重

## 8. Feature Graph

| 关系 | 构建方式 |
|------|---------|
| `requires` | 按 SV 构造依赖规则 (class extends → requires class, always_ff → requires clock) |
| `co_occurs` | 同一 issue 提取的特征互为 co_occurs |
| `conflicts` | 初始为空, 后续可添加规则 |
| `rarity_score` | 0.40×complexity + 0.30×tag_rarity + 0.15×cold_bonus + 0.15×tool_score |

## 9. 输出格式

必须通过 `/edazz/EDAzz/tools/contracts.py:validate_feature_dataset()`.

**顶层 keys**: `schema_version`, `features`, `feature_index`, `feature_graph`, `source_summary`, `build_info`

```json
{
  "schema_version": 1,
  "features": [
    {
      "feature_id": "feat.history_v2.a1b2c3d4e5f6",
      "name": "queue assignment to large unpacked array",
      "category": "data_model",
      "description": "Code should include ...",
      "source": "history_v2",
      "tags": ["queue", "unpacked_array", "data_model"],
      "metadata": {
        "snippet": "byte unsigned word[257]; ...",
        "source_bug_id": "6988",
        "tool": "verilator",
        "issue_url": "https://github.com/verilator/verilator/issues/6988",
        "construct_complexity": 2,
        "ub_type": null,
        "error_pattern": "cpp_compile_error"
      }
    }
  ],
  "feature_index": { "by_id": {...}, "by_category": {...}, "by_source": {...} },
  "feature_graph": { "feat.history_v2.xxx": { "requires": [], "conflicts": [], "co_occurs": [], "rarity_score": 0.35 } },
  "source_summary": { "total_features": N, "by_source": {"history_v2": N} },
  "build_info": { "built_at": "...", "builder": "history-issue-features/merge.py", "source_revision": "..." }
}
```

## 10. 运行配置

`config.yaml` 支持多 provider 并行, 每个 provider 可配置 concurrency:

```yaml
timeout: 600
subagent_parallelism: 2

providers:
  - name: "kimi3"
    concurrency: 1              # 该 provider 的并行 slot 数
    env:
      ANTHROPIC_BASE_URL: "https://api.kimi.com/coding/"
      ANTHROPIC_AUTH_TOKEN: "sk-kimi-..."
```

**运行方式**: tmux 后台, 不阻塞主工作

```bash
# 爬取
tmux new -d -s crawl 'python3 -u scripts/crawl_issues.py --full'

# 提取 (爬取完成 + 框架验证通过后)
tmux new -d -s extract 'python3 -u run-all.py'

# 合并
python3 merge.py
```

## 11. 增量更新

| 组件 | 增量策略 |
|------|---------|
| `crawl_issues.py` | `crawl_state.json` 记录上次时间, `?since=` 增量追加 |
| `prepare_inputs.py` | 仅为新 issue 生成 issue_input.json |
| `run-all.py` | 跳过已有 output/features.json 的 issue |
| `merge.py` | 始终从所有 per-issue 输出重新合并 (毫秒级) |

## 12. 实现阶段

| Phase | 内容 | 状态 |
|-------|------|------|
| A | 项目骨架 + 数据爬取 (16,997 条) | 已完成 |
| B | 框架构建 (agents, hooks, runners, merge) | 已完成 |
| C | 小规模测试 (8 issues, 40 features, EDAzz 验证 PASSED) | 已完成 |
| D | 全量处理 (6,819 issues, kimi3, tmux 后台) | 运行中 |

## 13. 数据统计

### 原始数据

| 来源 | Issues | PRs | 合计 |
|------|--------|-----|------|
| Verilator | 4,500+ | 2,300+ | 6,812 |
| CIRCT | 2,600+ | 7,500+ | 10,185 |
| **合计** | | | **16,997** |

### 筛选后

| 来源 | 纳入 | 排除 | 纳入率 |
|------|------|------|--------|
| Verilator | 3,473 | 3,339 | 51% |
| CIRCT | 3,354 | 6,831 | 33% |
| **合计** | **6,827** | | |

### 预估产出

| 指标 | 预估值 |
|------|--------|
| 可提取 issue 数 | ~1,700 |
| 原始特征数 | 3,800-7,600 |
| 去重后特征数 | 2,000-4,000 |

## 14. 关键依赖

| 依赖 | 用途 |
|------|------|
| `/edazz/mirtl-pocs/issues/` | 基线爬取数据 |
| `/edazz/ieee-spec-features/` | 参考架构 (WorkerPool, agent, hook 模式) |
| `/edazz/FeatureFuzz-SV/data/feature_pool.json` | 去重基准 (891 条 legacy 特征) |
| `/edazz/EDAzz/tools/contracts.py` | 输出格式权威定义 |
| GitHub CLI (`gh`) | 数据爬取 |
| Claude Code CLI (`claude`) | Agent 执行 |
