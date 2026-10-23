# EvidencePilot-RL 项目调研与立项方案

## 1. 结论

建议实现 **EvidencePilot-RL：可训练的证据驱动研究智能体**。

它不是客服机器人，也不是伪装成生产级 Coding Agent，而是一个可复现的多轮 Agentic RL 项目：模型在离线文档环境中自主规划、检索、阅读、记录证据、纠错并提交带引用的答案；先用 ReAct/SFT 建立基线，再用 GRPO 优化工具选择和多跳检索策略。

项目重点不是做一个聊天页面，而是打通四条真正有含金量的链路：

1. 可持久化、可恢复、可回放的 Agent Harness；
2. 可自动判分的多轮工具环境；
3. 轨迹数据生产、过滤与评测；
4. 基于 veRL/verl-agent 的 GRPO 训练及消融实验。

## 2. 值得借鉴的开源项目

| 项目 | 值得学习的部分 | 本项目借鉴方式 |
| --- | --- | --- |
| [LangGraph](https://github.com/langchain-ai/langgraph) | 状态图、检查点、故障恢复、长周期任务 | 借鉴状态模型，但核心 Harness 自己实现，避免项目只是“调库” |
| [smolagents](https://github.com/huggingface/smolagents) | 极简 Agent loop、工具抽象、模型无关 | 保持运行时小而可读，工具统一为结构化输入输出 |
| [DeerFlow](https://github.com/bytedance/deer-flow) | 长任务、记忆、子任务、沙箱和消息网关 | 只取“长任务状态与证据管理”，不复制其庞大产品层 |
| [GPT Researcher](https://github.com/assafelovic/gpt-researcher) | 研究任务的规划、检索、报告生成与评测 | 借鉴研究工作流，但把“生成报告”改成可验证的证据任务 |
| [Search-R1](https://github.com/PeterGriffinJin/Search-R1) | 推理与搜索交错、观察 token mask、结果奖励 | 作为 Agentic RL 的直接算法基线 |
| [verl-agent](https://github.com/langfengQ/verl-agent) | 多轮 rollout、长 horizon、GRPO/GiGPO、记忆模块 | 作为正式训练后端，实现自定义环境适配器 |
| [Agent Lightning](https://github.com/microsoft/agent-lightning) | Agent 执行与训练解耦、轨迹与信用分配 | 训练接口不侵入 Harness，保持 eval/train 使用同一套 Agent 代码 |
| [rLLM](https://github.com/rllm-org/rllm) | 任意 Harness、沙箱、评测与多训练后端 | 参考其 rollout 接口设计；首版不直接依赖，控制复杂度 |

## 3. 关键论文脉络

1. [ReAct](https://arxiv.org/abs/2210.03629)：交错生成 reasoning 与 action，是 Agent loop 的基础。
2. [Reflexion](https://arxiv.org/abs/2303.11366)：通过语言反馈和情景记忆修正后续尝试，适合错误恢复基线。
3. [DeepSeekMath / GRPO](https://arxiv.org/abs/2402.03300)：用组内相对奖励代替 PPO 的价值模型，降低显存和训练复杂度。
4. [Search-R1](https://arxiv.org/abs/2503.09516)：用 RL 学习何时搜索、搜什么以及何时停止，证明结果奖励可训练搜索型 Agent。
5. [RAGEN](https://arxiv.org/abs/2504.20073)：指出多轮 RL 容易出现奖励方差塌陷和浅层策略，需要轨迹过滤、合理交互粒度和细粒度奖励。
6. [GiGPO](https://arxiv.org/abs/2505.10978)：在 episode 级相对优势之外增加 state/action 级信用分配，适合作为进阶消融，而不是首版主算法。
7. [Agent Lightning](https://arxiv.org/abs/2508.03680)：把任意 Agent 执行轨迹转成训练 transition，强调 Harness 与训练系统解耦。

## 4. 为什么选择 GRPO

GRPO 是项目的主训练算法，原因是：

- 市面常见：veRL、verl-agent、rLLM、ART 均提供或围绕 GRPO 构建能力；
- 比 PPO 更适合个人项目：不需要额外训练 critic/value model；
- 天然适合可自动判分任务：同一个问题采样多条轨迹，按组内结果比较优劣；
- 能清晰做实验：ReAct、SFT、Outcome-only GRPO、Shaped-reward GRPO 四组对照。

GiGPO 只作为可选扩展。如果首版数据中存在足够多的重复环境状态，再加入 step-level 相对优势；否则强行使用会增加复杂度却没有可信收益。

## 5. 项目设计

### 5.1 Agent 任务

输入一个需要两到四跳证据的问题，Agent 在受控文档环境中调用：

- `search(query, top_k)`：检索候选段落；
- `read(doc_id)`：读取文档或段落；
- `save_evidence(doc_id, sentence_id, claim)`：登记“结论—证据”关系；
- `revise_plan(reason)`：显式记录失败归因和新计划；
- `finish(answer, citations)`：提交答案与句子级引用。

首版采用 HotpotQA 的 supporting facts 构建每题离线文档池，保证奖励完全可复现；之后用 MuSiQue 做跨数据集泛化评测。

### 5.2 Harness 状态

```text
RunState
├── task / budget / current_step
├── plan
├── observations
├── evidence_ledger
├── tool_errors
├── compact_summary
└── final_answer / citations / reward
```

运行时支持：

- SQLite 检查点与断点恢复；
- JSONL 事件流和完整轨迹回放；
- token/步骤/工具预算；
- 工具超时、空结果、非法参数的错误恢复；
- 上下文压缩，但永久保留任务、计划、证据账本和错误摘要；
- eval 与 training 共用同一个 Agent loop。

### 5.3 可解释的奖励函数

首版不用主观 LLM Judge 作为核心奖励，尽量使用数据集真值：

```text
R = 0.50 * answer_f1
  + 0.25 * supporting_fact_f1
  + 0.15 * citation_precision
  + 0.10 * valid_finish
  - 0.02 * excess_steps
  - invalid_tool_penalty
```

这样可以同时优化“答对”“证据对”“调用合法”和“步骤不过度”，也便于定位 reward hacking。训练时只对模型生成的 reasoning/action token 计算 loss，检索返回的 observation token 做 mask。

### 5.4 创新点

1. **Evidence Ledger**：不是把检索文本全部堆入上下文，而是维护 claim—document—sentence 的显式证据关系。
2. **Failure-aware Recovery**：在空检索、冲突证据、无效引用和预算不足时执行可观测的重规划，并单独统计恢复成功率。
3. **Evidence-aware GRPO**：对比只看最终答案的 outcome reward 与答案、证据、引用、效率组成的 shaped reward。
4. **Replayable Agent Harness**：任意失败轨迹可从检查点重放，固定工具观察以复现实验，而不是只能看日志猜问题。

这些点都能真正实现和验收，不需要宣称“自研大模型”或“生产级多智能体平台”。

## 6. 数据与评测

数据：

- [HotpotQA](https://github.com/hotpotqa/hotpot)：有答案和句子级 supporting facts，适合训练及自动奖励；
- [MuSiQue](https://github.com/StonyBrookNLP/musique)：由多跳问题组合构成，适合检验泛化；
- 可选 [FEVER](https://github.com/awslabs/fever)：用于扩展到证据支持/反驳/信息不足分类。

对比实验：

| 实验组 | 用途 |
| --- | --- |
| Direct RAG | 检查多轮 Agent 是否真的有价值 |
| ReAct Prompting | 不训练的 Agent 基线 |
| Rejection-Sampling SFT | 验证高质量成功轨迹的收益 |
| GRPO outcome-only | 标准 Agentic RL 基线 |
| GRPO shaped reward | 验证证据奖励和效率惩罚 |

指标：Answer EM/F1、Supporting Fact EM/F1、Citation Precision/Recall、任务成功率、非法工具调用率、平均步骤数、平均 token、错误恢复成功率。

## 7. 技术栈与算力策略

- Python 3.11、Pydantic、asyncio、FastAPI；
- SQLite + JSONL 作为状态与事件存储；
- BM25 作为确定性基线，后续加入 dense retriever/reranker；
- vLLM 或 SGLang 做批量 rollout；
- veRL/verl-agent + GRPO 做训练；
- MLflow 或 W&B 记录训练曲线和轨迹指标；
- pytest + Docker 保证复现。

本机 RTX 4060 Laptop 只有 8GB 显存：适合开发 Harness、数据、评测和量化小模型推理，不适合原生 veRL 多轮训练。正式 GRPO 计划在短租 48GB/80GB GPU 上完成；代码仍提供 CPU/mock 模式，让仓库可以零 GPU 跑通测试。

## 8. 实施阶段

1. **MVP Harness**：状态机、工具、检查点、轨迹、预算、错误恢复；
2. **离线环境**：HotpotQA 文档池、BM25、确定性 scorer；
3. **基线与数据飞轮**：Direct RAG/ReAct、成功轨迹筛选、SFT 数据导出；
4. **Agentic RL**：verl-agent 环境适配、GRPO、observation mask、训练配置；
5. **实验与发布**：完整消融、错误归因、README 动图、模型卡、Docker、GitHub Actions。

## 9. 简历边界

项目完成前只写“正在构建/实现”；训练与评测完成后，简历只填真实跑出的指标。GitHub 链接也应在仓库具备可运行 MVP、测试和 README 后再公开，避免空仓库。
