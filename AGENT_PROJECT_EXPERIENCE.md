# LuluStudio Agent 项目经历（Agent 岗位版）

## 一、项目名称

### LuluStudio Agent：固定 IP 短剧生成与自进化质量优化智能体｜个人项目

**项目时间：** `[按真实时间填写]`
**项目角色：** 独立开发
**核心技术：** Python、FastAPI、Pydantic、SQLite、ComfyUI API、AutoDL、F.1/FLUX LoRA、MiniMax 多图生视频、IndexTTS-2.5、CosyVoice 3、向量检索、veRL/GRPO

> 技术栈中只保留真正接入并产生实验记录的组件。若 IndexTTS、向量检索或 GRPO 尚未跑通，投递前删除或改成“设计/规划”。

## 二、一页简历推荐版

- 面向固定 IP“水豚噜噜”的短剧生产流程，设计并实现可持久化 Agent Harness，以 `Episode—Scene—Shot—Attempt` 状态模型统一管理剧本、分镜、关键帧、视频、配音和评测结果，支持任务中断恢复、镜头级 checkpoint、失败重试、预算控制及版本追踪。
- 设计结构化 Production IR，将角色身份、角色实例、动作、景别、关键帧、视频参数、台词、音色和时长约束转化为可校验任务；通过 Tool Registry 编排 ComfyUI、F.1 角色 LoRA、MiniMax 多图生视频和 TTS 服务，实现工具参数校验、幂等调用、超时重试与结果回写。
- 构建短期状态与长期经验记忆：短期状态保存当前镜头依赖、尝试次数和剩余预算，长期记忆沉淀历史“场景—缺陷—修复动作—质量变化—成本”轨迹；Recovery Planner 检索相似案例并按成功率、预计收益与生成成本选择局部修复动作。
- 建立固定 IP 专属多模态评测与归因体系，覆盖毛发细节、长镜头身份漂移、双角色实例绑定、异常主体、动作完成度、语音音色/情绪/时长及音画同步；根据缺陷发生阶段选择提示词改写、参数调整、末帧续接、镜头拆分、区域约束、分层生成或语音重合成，避免整集重复生成。
- 将人工 A/B 选择、自动指标和恢复轨迹转化为 Agentic SFT/偏好数据；在完成基线后使用 veRL/GRPO 优化恢复策略，以硬约束通过、质量增量和成本惩罚构造奖励，对比规则、检索、SFT 与 GRPO 策略在镜头通过率、平均重试次数、人工偏好胜率和单镜头成本上的差异。

## 三、当前阶段可直接使用的诚实版

如果目前已经完成 ComfyUI + MiniMax 工作流和人工实验，但 Agent Harness、TTS、自动评测、GRPO 仍在开发，简历使用下面这版：

### LuluStudio Agent：固定 IP 短剧生成与质量进化系统｜个人项目

**技术栈：** Python、ComfyUI、AutoDL、F.1/FLUX LoRA、MiniMax、多图生视频、Prompt Engineering

- 基于 AutoDL 搭建“水豚噜噜”固定 IP 的 ComfyUI 多图生视频工作流，使用 F.1 角色 LoRA 生成分镜关键帧并接入 MiniMax 完成视频合成，记录提示词、LoRA 权重、采样参数、随机种子、输入图及输出结果，实现镜头级实验复现。
- 围绕毛发模糊、塑料质感、长镜头身份漂移、双角色远景异常和视频细节衰减开展 A/B 试验，将人工接受/拒绝、缺陷标签及修改偏好整理为角色专属评测标准、正反例锚点和可复用生成配方。
- 将生成问题按“关键帧—多图一致性—视频生成—后处理”分阶段归因，并设计镜头切分、末帧续接、区域约束、角色分层生成和局部重试等恢复动作，减少对已通过素材的重复生成。
- 设计 Agent 化改造方案，定义 Production IR、镜头状态、工具调用协议、轨迹日志和 Recovery Planner；计划通过历史案例检索选择低成本修复策略，并将人工 A/B 反馈沉淀为后续 SFT/GRPO 数据。
- 当前使用 MiniMax 自动语音，已完成 IndexTTS-2.5/CosyVoice 3 的接入选型，设计噜噜/噜妹独立 Voice Card、说话人绑定及音色、情绪、时长和音画同步评测方案。

这一版没有声称已经完成 Agent 训练，但能说明已有真实生产链路、问题发现和清晰的 Agent 落地设计。

## 四、项目背景与问题定义

原始生产方式是在 AutoDL 中手工运行 ComfyUI：使用 F.1/FLUX 角色 LoRA 生成噜噜关键帧，再通过 MiniMax 多图生视频得到短视频片段。实际试错中出现以下问题：

- 相同提示词和参数无法保证不同镜头中的角色稳定；
- 镜头越长，脸型、体型、毛发和服装越容易随时间漂移；
- 两个距离较远的噜噜同框时，容易身份融合、主体数量错误或生成额外物体；
- 输入关键帧正常，但进入视频或后处理后毛发细节被抹平或闪烁；
- MiniMax 自动配音难以稳定复现噜噜与噜妹的音色、情绪和台词时长；
- 手工返工依赖个人经验，无法复现“为什么这次修改有效”。

项目目标不是再做一层聊天界面，而是将生成工具、人工经验和质量反馈封装成能够持续执行、失败恢复并积累经验的 Agent Runtime。

## 五、Agent 系统设计

### 5.1 Agent Harness

Harness 负责运行而不是负责“想象内容”，核心能力包括：

```text
任务创建
  → 状态持久化
  → 调用生成工具
  → 收集结果
  → 自动/人工评测
  → 选择恢复动作
  → 局部重试
  → checkpoint
  → 输出成片与完整轨迹
```

状态层级：

```text
Episode
└── Scene
    └── Shot
        └── Attempt
            ├── input_state
            ├── tool_call
            ├── artifact
            ├── metrics/defects
            ├── recovery_action
            └── cost/latency
```

所有长周期任务写入 SQLite；每个工具调用拥有 `run_id` 和幂等键，进程中断后从最近成功 checkpoint 恢复，而不是重新运行整集。

### 5.2 Production IR 与上下文工程

Agent 不直接把整段剧本塞给所有工具，而是维护结构化 Production IR：

```yaml
shot_id: ep01_sc02_sh03
duration_budget_ms: 5000
character_instances:
  - instance_id: lulu_left
    identity_id: lulu
    region: left
    action: wave
  - instance_id: lumei_right
    identity_id: lumei
    region: right
    action: look_at_left
visual:
  keyframes: []
  comfy_workflow: lulu_two_character_v1
  video_backend: minimax
dialogue:
  speaker_instance_id: lulu_left
  voice_id: lulu_voice_v1
  emotion: happy
  target_duration_ms: 4200
constraints:
  expected_instance_count: 2
  forbid_extra_subjects: true
```

给每个 Agent 节点的上下文仅包含当前任务需要的信息：例如 Media QA 不需要完整剧本，只需要当前镜头约束、角色参考和生成结果；Recovery Planner 读取缺陷、历史尝试、相似案例和剩余预算，避免长上下文持续膨胀。

### 5.3 工具调用与编排

工具统一注册为结构化接口：

```text
generate_keyframes
generate_video
synthesize_voice
evaluate_visual
evaluate_audio
compose_timeline
retrieve_cases
save_checkpoint
```

每个工具均定义 Pydantic 输入输出、超时、最大重试次数、可重试错误和产物路径。工具返回的不只是文件地址，还包括模型版本、参数、时延、成本和错误类型。

推荐部署：

- ComfyUI：关键帧生成和后处理；
- MiniMax Adapter：多图生视频；
- IndexTTS-2.5/CosyVoice 3：独立 FastAPI TTS 服务；
- Agent Harness：负责队列、状态、工具调用、评测和恢复；
- 单 GPU 环境串行加载/卸载模型，避免图像、视频、语音模型争抢显存。

### 5.4 记忆系统

**短期记忆**保存当前 Episode/Shot 状态、工具输出、尝试历史、依赖和预算。
**长期记忆**保存已经验证的角色参考、Voice Card、提示词配方、典型失败、修复动作及其适用条件。

长期案例结构：

```json
{
  "context": {
    "shot_type": "two_character_wide",
    "duration_sec": 8,
    "motion_level": "medium"
  },
  "defects": ["extra_subject", "lulu_right_identity_drift"],
  "action": "split_layers_and_composite",
  "quality_delta": 0.18,
  "human_preference": "accepted",
  "cost": 2.6
}
```

检索时先用结构化条件过滤镜头类型、角色数量和生成阶段，再用向量相似度检索文本化案例，避免只靠 embedding 找到语义相似但生产条件不同的经验。

### 5.5 Recovery Planner

Planner 的动作空间是有限且可执行的，不允许自由生成无法落地的建议：

```text
rewrite_prompt
adjust_lora_weight
replace_keyframe
reuse_last_accepted_frame
split_shot
reduce_motion_complexity
apply_region_conditioning
split_character_layers
switch_workflow
adjust_voice_speed
replace_emotion_reference
split_dialogue
regenerate_failed_segment_only
```

动作选择顺序综合考虑：

```text
expected_utility
= predicted_quality_gain
 + historical_success_rate
 - generation_cost
 - latency_penalty
 - repeated_action_penalty
```

优先执行低成本、可局部回滚的修复；相同动作连续失败后必须升级策略或请求人工判断，防止 Agent 陷入无效循环。

## 六、视觉与语音联合评测

### 6.1 视觉评测

- `identity_similarity`：当前角色与噜噜参考集的身份相似度；
- `identity_drift_curve`：长镜头中身份质量随时间的变化；
- `fur_detail_retention`：关键帧进入视频后的毛发细节保持率；
- `instance_count_accuracy`：双角色镜头是否始终保持指定角色数量；
- `per_instance_identity`：左右角色分别进行身份检查；
- `instance_binding_accuracy`：位置、动作和道具是否属于正确角色；
- `extra_object_rate`：额外角色、肢体或道具的出现比例；
- `motion_amount_fit`：动作是否满足分镜，防止用静止画面换取一致性。

### 6.2 语音与音画评测

- `cer/wer`：生成语音与目标台词的一致性；
- `speaker_similarity`：是否保持噜噜或噜妹的固定音色；
- `emotion_match`：语音情绪是否符合当前动作；
- `duration_error_ms`：台词是否落入镜头时长预算；
- `prosody_naturalness`：停顿、重音和语速是否自然；
- `lip_sync`：仅对嘴部清晰可见的对白镜头评测。

可见嘴部的对白采用“语音优先”：先生成语音并取得真实时长，再规划/调整镜头；远景、背影和旁白只做时间线对齐，不强行使用真人口型模型处理非人类角色。

## 七、经验蒸馏与 Agentic RL

### 7.1 数据构造

每次尝试保存：

```text
state
→ candidate_action
→ tool_result
→ stage_metrics
→ human_accept/reject
→ preference_reason
→ quality_delta
→ cost
```

数据按相同初始状态组织成候选组：例如同一个“长镜头角色漂移”分别尝试缩短镜头、复用末帧和改提示词，由人工 A/B 及自动硬指标确定相对偏好。

### 7.2 训练顺序

1. 规则基线：验证状态、工具和评测链路；
2. 检索增强策略：复用历史成功案例；
3. Agentic SFT：学习成功轨迹中的动作选择与参数生成；
4. GRPO：在相同状态下生成一组恢复动作，通过相对奖励优化策略；
5. 回归评测：确认质量提高没有以成本暴涨、静态作弊或角色设定破坏为代价。

奖励建议：

```text
reward
= hard_constraint_pass
 + quality_delta
 + human_preference
 + final_completion_bonus
 - generation_cost
 - retry_penalty
 - invalid_tool_call
 - static_cheating_penalty
```

这里训练的是“发生某类失败后应该选择什么恢复动作”，不是训练底层视频生成模型，也不声称小数据能够直接提升 MiniMax 本身。

## 八、项目创新点

1. **固定 IP 经验蒸馏**：将创作者对毛发、脸型、角色气质等隐性判断转化为版本化 criterion、正反例锚点和修复轨迹。
2. **阶段化质量归因**：区分关键帧、多图规划、视频生成和后处理造成的退化，避免在错误阶段反复调参。
3. **长视频片段级恢复**：使用身份漂移曲线定位退化时刻，通过 checkpoint 只回滚失败片段。
4. **同身份多实例绑定**：将“两个噜噜”表示为同一 identity 下的不同 instance，分别检查位置、动作、身份和额外主体。
5. **视觉—语音统一 Production IR**：把角色音色、情绪和台词时长与画面角色实例绑定，纳入同一个 Agent 状态和恢复闭环。
6. **成本感知 Agentic RL**：奖励质量增量和最终完成，同时惩罚无效重试、昂贵动作和静态作弊，使策略适合单卡/小作坊生产。

## 九、项目量化指标

没有真实实验前不要填写数字。实现后从数据库自动统计：

```text
累计运行：[X] 个镜头 / [X] 次生成尝试
缺陷体系：[X] 类缺陷 / [X] 个正反例锚点
镜头最终通过率：[X]% → [X]%
平均重试次数：[X] → [X]
人工 A/B 胜率：检索/GRPO 相比规则基线提升 [X] 个百分点
长镜头身份漂移发生率：下降 [X]%
双角色异常主体率：下降 [X]%
角色语音一致性人工评分：[X] → [X]
单镜头 GPU 时间或生成成本：下降 [X]%
中断任务恢复成功率：[X]%
```

## 十、面试一分钟介绍

我之前在 AutoDL 上用 ComfyUI、F.1 噜噜 LoRA 和 MiniMax 做过多图生视频，实际遇到的难点不是模型不会生成，而是长镜头角色会漂移、两个远距离角色容易出现额外主体、毛发细节会在视频阶段丢失，而且每次返工都依赖人工经验。于是我把这条链路改造成 LuluStudio Agent：通过 Production IR 管理镜头、角色实例、视频和配音约束，用可持久化 Harness 编排 ComfyUI、MiniMax 和 TTS 工具；生成后进行分阶段评测，Recovery Planner 根据缺陷、历史案例和剩余预算选择镜头拆分、末帧续接、区域约束或语音重合成等局部动作。系统记录完整状态—动作—结果—人工偏好轨迹，先做规则和检索基线，数据积累后再用 SFT 和 GRPO 学习成本受约束的恢复策略。这个项目的重点不是通用聊天，而是让 Agent 在真实多模态生产环境里能够持续执行、发现失败、恢复并从反馈中积累经验。

## 十一、避免夸大的表述边界

- 只有代码完成并通过中断恢复测试后，才写“实现 Agent Harness”；
- 只有真实接入模型并保存生成样例后，才写“接入 IndexTTS/CosyVoice”；
- 只有存在训练脚本、checkpoint、对照组和指标后，才写“使用 GRPO 优化”；
- 若只是调用现成模型，不写“训练视频生成模型”或“优化 MiniMax 模型”；
- 不编造播放量、完播率、成本下降和通过率；
- 模型许可证、角色 IP 和参考声音授权分别核验，技术可行不代表可以任意商用。
