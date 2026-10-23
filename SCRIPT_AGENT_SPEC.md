# DramaForge-RL：短剧剧本打磨智能体

## 1. 项目定位

DramaForge-RL 是一个面向中文竖屏短剧的长文本编辑 Agent。输入故事梗概、人物设定或初稿后，系统不会只做一次性“润色”，而是围绕剧本目标持续执行：结构诊断、角色与时间线检查、单场改写、前后文校验、版本比较和迭代停止判断，最终输出修改稿、修改依据和可回滚 diff。

首版聚焦 **已有剧本的诊断与打磨**，不承诺从零自动创作完整商业短剧。这个边界更容易实现、评测和在简历中自证。

## 2. 核心使用场景

输入：

- 剧本正文或分集梗概；
- 类型、受众、单集时长和目标集数；
- 不可修改的角色设定、核心冲突、结局或平台限制；
- 用户希望解决的问题，例如“前三集不够抓人”“角色动机不成立”。

输出：

- 剧本体检报告：节奏、冲突、钩子、人物、连续性、对白和格式；
- 按严重程度排序的问题清单；
- 场景级修改计划；
- 带 diff 的修改版本，而不是覆盖原稿；
- 每项修改的原因、影响范围和置信度；
- 尚未解决的问题及人工确认点。

## 3. Agent 工作流

```text
导入剧本
  ↓
结构化解析：集 → 场 → 动作/对白
  ↓
建立 Story Bible：人物、关系、时间线、伏笔、约束
  ↓
并行诊断
  ├─ 结构/节奏 Critic
  ├─ 人物动机 Critic
  ├─ 连续性 Critic
  └─ 对白/可拍性 Critic
  ↓
Orchestrator 合并、去重并排序问题
  ↓
Rewriter 按场景做最小必要修改
  ↓
Verifier 检查硬约束、前后文和修改副作用
  ↓
通过 → 输出版本与 diff
失败 → 带失败原因重新规划，最多 N 轮
```

这些“角色”是可观测的 Agent 节点，共享同一个剧本状态；首版不把它们包装成多个相互聊天的万能模型。

## 4. Harness 与状态设计

```text
ProjectState
├── project_brief
├── immutable_constraints
├── episodes[]
│   └── scenes[]
├── story_bible
│   ├── characters
│   ├── relationships
│   ├── timeline
│   ├── foreshadowing_payoffs
│   └── world_rules
├── issues[]
├── edit_plan[]
├── versions[]
├── unresolved_conflicts[]
└── budget / status / checkpoints
```

Harness 必须支持：

- SQLite 状态持久化和中断恢复；
- 事件流与完整轨迹回放；
- 场景级版本、diff 和回滚；
- 只向模型提供当前场景、邻近场景和相关 Story Bible 条目，控制长上下文；
- 工具超时、结构化输出错误和修改冲突后的重试；
- 用户锁定片段，Agent 不得修改；
- 每次修改记录 issue_id，保证“为什么改”可追踪。

## 5. 工具设计

- `parse_script`：解析集、场、角色、对白、动作和地点；
- `query_story_bible`：按人物/事件查询长期记忆；
- `check_character_consistency`：检测身份、关系、知识边界和行为动机冲突；
- `check_timeline`：检测时间、地点、出场和因果矛盾；
- `check_foreshadowing`：维护伏笔—回收账本；
- `score_scene`：给出钩子、冲突、信息增量、对白和可拍性分项结果；
- `rewrite_scene`：只修改指定场景并返回结构化 patch；
- `apply_patch`：验证版本号与锁定范围后应用修改；
- `compare_versions`：生成场景级 diff 和指标变化；
- `finish_revision`：提交最终版本与未解决问题。

## 6. 可实现的创新点

### 6.1 Story Bible 不是普通向量记忆

将角色事实、关系变化、时间线、世界规则和伏笔分别建模。每个条目带来源场景、有效时间范围、置信度和冲突状态，避免“召回到相关文本”就等于“理解连续性”。

### 6.2 Issue-driven Editing

Agent 不能直接大段重写。每个修改必须关联一个可验证 issue，并声明目标、修改范围和不可破坏的约束。这可以减少无意义改写和模型越改越偏。

### 6.3 Constraint-preserving Patch

修改器输出结构化 patch；应用前检查锁定台词、人物事实、场景顺序、长度预算和版本号。若破坏硬约束，拒绝修改并把错误返回 Agent 重规划。

### 6.4 Failure-aware Reflection

Verifier 不只返回“失败”，还输出失败类型：遗漏问题、制造新矛盾、角色失真、节奏变慢、过度改写或格式非法。Agent 根据失败类型选择重新检索记忆、缩小修改范围或更换修改策略。

## 7. 数据工程

不直接抓取或发布未经授权的商业短剧剧本。数据来源限定为：

- 自己编写或模型生成后人工审核的短剧样本；
- 公版故事的短剧化改编；
- 用户明确授权的文本；
- 从合成剧本中自动注入缺陷得到的训练任务。

缺陷注入类型：

- 人物身份/关系矛盾；
- 时间线冲突；
- 角色知道了不该知道的信息；
- 伏笔未回收或回收对象错误；
- 场景没有冲突或信息增量；
- 集尾缺少钩子；
- 对白同质化；
- 改写破坏锁定设定；
- 为了修一个问题造成新的前后文矛盾。

每条任务保存原稿、缺陷标签、受影响场景、约束、参考修复和验收规则，可同时用于 SFT、偏好数据和 RL 环境。

## 8. Agentic RL 方案

### 8.1 为什么不能只用“剧本好不好”作为奖励

叙事质量高度主观，如果直接让另一个 LLM 打总分，训练容易学会迎合 Judge、扩大改写幅度或堆砌冲突。因此奖励必须由确定性约束、缺陷修复和偏好评价共同组成。

### 8.2 主算法

使用 **GRPO + veRL/verl-agent**。同一个缺陷剧本采样多条“诊断—工具调用—修改—验证”轨迹，通过组内相对奖励优化 Agent 的工具选择和修改策略。

训练只更新模型生成的分析、动作和 patch token；原剧本与工具观察 token 做 loss mask。

### 8.3 奖励函数

```text
R = 0.30 * defect_fix_rate
  + 0.20 * constraint_pass_rate
  + 0.15 * no_regression_score
  + 0.15 * pairwise_quality_score
  + 0.10 * edit_precision
  + 0.10 * valid_trajectory
  - step_cost
  - excessive_rewrite_penalty
```

- `defect_fix_rate`：已知注入缺陷是否修复；
- `constraint_pass_rate`：锁定设定、格式、篇幅和连续性是否通过；
- `no_regression_score`：是否产生新的矛盾；
- `pairwise_quality_score`：Judge 在原稿和修改稿间做盲评；
- `edit_precision`：修改是否集中在必要片段；
- `valid_trajectory`：工具格式和终止条件是否合法。

### 8.4 实验组

1. 单次 Prompt 润色；
2. 未训练的 ReAct 编辑 Agent；
3. 成功轨迹 Rejection-Sampling SFT；
4. 只看最终缺陷修复率的 GRPO；
5. 完整多维奖励 GRPO；
6. 可选：加入 Reflexion 后的 GRPO。

## 9. 评测指标

- 缺陷检出 Precision / Recall / F1；
- 已知缺陷修复率；
- 新增矛盾率；
- 硬约束通过率；
- 场景级有效修改比例；
- 平均修改字符占比；
- 人工或盲评模型的 pairwise win rate；
- 平均工具步数、token 和失败恢复成功率；
- 长剧本角色事实与时间线一致率。

所有简历数据均在实验完成后填写，不预设提升百分比。

## 10. 实施路线

### Phase 1：可运行 MVP

- 剧本 Markdown/JSON 格式；
- 解析器、Story Bible、SQLite 项目状态；
- 连续性检查、结构化 issue、场景 patch、diff/回滚；
- 一个模型完成 Critic—Rewrite—Verify 循环；
- CLI 和测试样例。

### Phase 2：评测数据

- 建立合成短剧生成与人工抽检流程；
- 实现 8 类缺陷注入器和确定性验收器；
- 建立 baseline、训练集和固定测试集；
- 轨迹筛选并导出 SFT 数据。

### Phase 3：Agentic RL

- 接入 verl-agent 多轮 rollout；
- 在云 GPU 上训练小参数开源模型；
- 完成 outcome-only 与 shaped reward 消融；
- 分析 reward hacking 和 bad cases。

### Phase 4：作品化

- FastAPI 服务；
- 简单 Web 页面：原稿/修改稿并排、问题列表、diff、版本时间线；
- Docker、GitHub Actions、架构图、演示视频、模型卡和实验报告。

## 11. 简历可写边界

在项目真实完成后，可以围绕以下事实写：

- 自主设计剧本编辑 Agent Harness，实现长文本状态持久化、Story Bible、场景级 diff/回滚和错误恢复；
- 构建短剧缺陷注入与轨迹评测流水线，覆盖人物、时间线、伏笔、节奏和约束保持；
- 基于 veRL/verl-agent 使用 GRPO 优化多轮诊断与编辑策略，对比 Prompt、SFT 和不同奖励设计；
- 建立缺陷修复率、新增矛盾率、修改精度、人工偏好胜率和工具效率等评测指标。

不能提前写“商业落地”“服务编剧团队”“提升 XX%”或“训练百亿模型”。
