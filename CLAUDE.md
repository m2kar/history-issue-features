# History Issue Features

从 Verilator/CIRCT 历史 GitHub Issue/PR 中提取 SystemVerilog 代码特征,
用于 EDAzz 差分 fuzzing 工具的特征库.

## 方法论

采用 FeatureFuzz 论文的 ExtractLLM 三步法:
1. **阅读理解**: 读取 bug report + root cause
2. **综合分析**: 联合分析 bug report + root cause + bug-triggering program
3. **抽象提取**: 从具体测试用例转化为抽象语义原语 (解耦, 独立, 可复用)

## 工作模式

当前工作目录为项目根 `/edazz/history-issue-features/`.

每个 issue/PR 的工作目录为 `issues/{tool}-{number}/`:
- `issue_input.json` -- 预处理后的输入
- `workspace/` -- 中间产物 (partial_*.json)
- `output/features.json` -- 最终输出

原始爬取数据位于 `raw/` 目录.

## Agent 角色

- **manager**: 实现 ExtractLLM 三步法, 理解 bug 语义, 分派 extractor
- **extractor**: 完成 "具体测试用例 -> 抽象语义原语" 的转换

## 约束

- 只读: `raw/`, `.claude/`
- 只写: `issues/*/workspace/` 和 `issues/*/output/` 目录
- snippet 格式: 仅核心语法, 不需要完整 module 包装
- description 格式: 必须以 "Code should include" 开头
- 提取原则: 解耦独立, 每个特征不引用其他特征

## 数据来源

- Verilator: `raw/verilator.jsonl` (GitHub Issues API)
- CIRCT: `raw/circt.jsonl` (GitHub Issues API)
- 基线数据: 复制自 `/edazz/mirtl-pocs/issues/`

## 输出

最终输出 `output/merged_history_v2_features.json` 必须通过
`/edazz/EDAzz/tools/contracts.py:validate_feature_dataset()` 验证.

## 依赖

- Python 3.12+
- PyYAML (仅 run-all.py)
- GitHub CLI (`gh`) -- 数据爬取
