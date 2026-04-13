# AGENT LOG

## 2026-04-13
**Session topic**: 从Verilator/CIRCT历史Issue提取SV特征系统完整搭建

### 用户输入

1. 设计完整技术方案: 设计从 Verilator/CIRCT 历史 issue/PR 提取 SystemVerilog 代码特征的系统. 参考 /edazz/ieee-spec-features/ 项目,特别是/edazz/ieee-spec-features/docs/01_design.md 以及整个项目的技术栈和代码结构. 能够输出符合 /edazz/EDAzz 要求的特征数据集.
2. (Plan mode feedback) 改为通过gh从 Verilator/CIRCT 的github issue/PR 爬取原始 issue/pr 信息并保存为原始信息. 然后参考FeatureFuzz论文ExtractLLM三步法提取特征. 注意最终格式要满足 EDAzz 要求.
3. (Plan mode feedback) 修改意见：1. Stage1 预处理中，不需要筛选 state == "close"， open 的也要。 circt 的 issue 筛选中，可以把包含 circt-verilog 的也纳入进来。 预处理筛选后，随机挑一些排除和未被排除的 issue，判定是否是误报/漏报，迭代优化筛选策略。2. Github 请求频率限制为每小时 2000 条，用 tmux 在后台获取。不阻塞主要工作。3. 框架构建完成后，先用 "xy7-minimax" provider 进行小规模测试，并检查结果是否正常。如果不正常，则优化整个框架直到正常。4. 等待github 数据准备完成，且框架运行效果较好之后。开启 tmux 在后台进行全量数据处理，单线程运行，provider 使用 "xy7-minimax" 。
4. continue until done
5. continue until done. use kimi3 provider.
6. 删除 agents 中关于 UB(Undefined Behavior) 的所有说明,直接在 hook 中把相关字段定义为空即可. 所有 Agent 文档要精简,按照ClaudeCode 官方文档的最佳实践,使用英文编写.
7. /log

### 变更记录

1. 在 `/edazz/history-issue-features/` 创建完整项目骨架：`CLAUDE.md`, `config.yaml`, `pyproject.toml`, `.claude/settings.json` 及目录结构 (raw/, issues/, output/, logs/)
2. 新增 `scripts/crawl_issues.py` 爬取脚本，从 GitHub 增量爬取 Verilator (6,812条) 和 CIRCT (10,185条) 的 issue/PR 数据到 `raw/*.jsonl`
3. 新增 `scripts/prepare_inputs.py` 预处理脚本，从 16,997 条原始数据中筛选出 6,827 个含 SV 内容的 issue，生成 `issues/*/issue_input.json`
4. 新增 `.claude/agents/manager.md` 和 `.claude/agents/extractor.md` 两个 Agent 定义，实现 FeatureFuzz ExtractLLM 三步法（阅读理解→综合分析→抽象提取），按 Claude Code 官方最佳实践以英文编写
5. 新增 `.claude/hooks/validate-feature.py` PreToolUse Hook，验证特征 schema 并通过 `updatedInput` 强制将 `ub_type`/`ub_quote` 设为 null
6. 新增 `run-issue.py`, `run-all.py` (WorkerPool 模式) 和 `merge.py` (去重+图构建+rarity+EDAzz兼容输出)，完整处理管道通过 EDAzz `validate_feature_dataset()` 验证
7. 完成 8 个 issue 的小规模测试（40个特征），验证格式正确后在 tmux `extract` 会话中启动全量处理（6,819个 issue，kimi3 provider 单线程）
