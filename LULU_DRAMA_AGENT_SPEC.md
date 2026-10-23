# LuluStudio Agent：噜噜短剧剧本—视频联合生产智能体

> 本文暂按“噜噜短剧”是自有 IP / 固定栏目名称设计。此前的通用剧本打磨方案降级为底层能力，本方案作为主项目定义。

## 1. 项目不是通用编剧工具

LuluStudio Agent 服务于“噜噜短剧”这一条具体生产线。它了解固定角色、视觉风格、声音、常用场景、单集时长、可用视频模型、镜头成本和发布规格；剧本修改的目标不是文学性最大化，而是在故事效果、可生成性、一致性和制作成本之间取得平衡。

最终输入、输出边界：

```text
选题/梗概/旧剧本
    ↓
噜噜短剧生产 Agent
    ↓
可直接消费的 Production Package
    ├── 分集剧本
    ├── 分镜与镜头依赖
    ├── 角色/场景/道具引用
    ├── 首帧图与视频提示词
    ├── 台词、旁白、音色和时长
    ├── 视频生成任务
    └── 剪辑时间线
```

视频生成系统再把每个镜头的结果、失败原因、成本和质量分数返回给 Agent，触发局部重写或重新生成。

## 2. 适合小作坊的固定化策略

项目不追求支持所有类型短剧，而是将“噜噜短剧”做成一个可配置的生产协议：

- 固定主角与配角集合；
- 固定角色参考图、音色和说话习惯；
- 固定画幅、画风、字幕与片头片尾；
- 固定若干高频场景和镜头模板；
- 固定单集时长、镜头数和生成预算；
- 控制单镜头角色数量、动作复杂度和台词长度；
- 优先复用已经验证稳定的角色、场景、提示词和种子。

配置示例：

```yaml
show:
  id: lulu_drama
  aspect_ratio: "9:16"
  episode_duration_sec: [45, 75]
  target_shots: [8, 14]

production_limits:
  max_characters_per_shot: 2
  max_dialogue_sec: 8
  max_generation_cost: 20
  prefer_asset_reuse: true

audio:
  primary_backend: indextts_2_5
  fallback_backend: cosyvoice_3
  baseline_backend: minimax_auto_voice

style:
  character_bible: assets/lulu/characters.yaml
  location_library: assets/lulu/locations.yaml
  voice_library: assets/lulu/voices.yaml
  shot_templates: assets/lulu/shot_templates.yaml
```

这些约束以后应由真实生成实验校准，不在项目开始时伪造最佳数值。

## 3. 统一的中间表示：Production IR

剧本 Agent 与视频生成端不能只通过自然语言提示词连接。两边共享结构化 `ProductionIR`：

```text
ProductionIR
├── show_profile
├── episode
│   ├── narrative_goal
│   ├── opening_hook
│   ├── ending_hook
│   └── duration_budget
├── scenes[]
│   ├── location_id
│   ├── characters[]
│   ├── continuity_state
│   └── shots[]
│       ├── shot_id / duration
│       ├── character_asset_ids / character_instances
│       ├── camera / composition
│       ├── action_beats
│       ├── dialogue / voice_id / emotion / target_speech_duration
│       ├── first_frame_prompt
│       ├── video_prompt
│       ├── negative_prompt
│       ├── backend / seed / model_version
│       └── dependencies
└── edit_timeline
```

Production IR 是项目最关键的工程资产：同一剧本可以换视频后端，视频端的失败也能精确定位到场、镜头、角色和提示词。

## 4. 闭环 Agent 工作流

```text
故事规划
  ↓
剧本与对白
  ↓
分镜规划
  ↓
生产可行性检查
  ↓
生成首帧/角色图/镜头视频/配音
  ↓
自动视觉与音频 QA
  ├─ 角色漂移
  ├─ 双角色身份污染/额外主体
  ├─ 场景/服装/道具不连续
  ├─ 动作未实现
  ├─ 台词与镜头时长不匹配
  ├─ 音画/口型问题
  └─ 成本或重试次数超预算
  ↓
Recovery Planner
  ├─ 只改提示词并重试
  ├─ 换镜头模板
  ├─ 拆分复杂镜头
  ├─ 复用上一通过片段的末帧
  ├─ 将双角色改为分层生成/区域约束
  ├─ 缩短或改写台词
  ├─ 用旁白替代难生成对白
  ├─ 复用已有素材
  └─ 必要时回退修改剧本
  ↓
局部重生成 → QA → 合成 → 发布包
```

Agent 不能一遇到失败就重写整集。恢复动作按成本从低到高执行，并记录每次决策。

## 5. Agent 节点

### Showrunner

维护本集目标、冲突、节奏和固定栏目风格，决定哪些叙事元素不可牺牲。

### Script Editor

在不破坏核心故事的前提下调整对白、动作和场景，所有修改输出场景级 patch。

### Storyboard Director

把场景拆成有限镜头，选择景别、机位、时长、角色资产和动作节拍。

### Production Planner

根据当前视频后端能力、历史成功率、预算和资产库选择生成方案。

### Media QA

分析生成图片、视频和音频，返回结构化缺陷及置信度。

长镜头按时间采样形成身份漂移曲线；双角色同框时分别检查实例数量、逐实例身份、空间/动作绑定及异常物体，不能只算整图相似度。

### Recovery Planner

基于缺陷类型、剩余预算和历史尝试选择最小修复动作。

长镜头漂移优先做片段级回滚、缩短片段或复用末帧；两个远距离噜噜生成异常时，优先换景别、分镜、区域 mask 或角色分层合成，只重生成失败实例。

这些节点共享同一状态和事件日志；可以并行分析，但不包装成无边界的“多智能体聊天”。

## 6. 视频端反馈协议

每次生成任务返回：

```json
{
  "shot_id": "ep01-sc02-sh03",
  "status": "failed_quality_check",
  "artifacts": {
    "video": "artifacts/...mp4",
    "audio": "artifacts/...wav"
  },
  "metrics": {
    "identity_consistency": 0.71,
    "prompt_alignment": 0.83,
    "audio_text_alignment": 0.97,
    "duration_error_ms": 420
  },
  "defects": [
    {
      "type": "character_drift",
      "severity": "high",
      "evidence_frame": 37
    }
  ],
  "cost": {
    "credits": 1.6,
    "latency_sec": 92
  },
  "backend": {
    "name": "adapter_name",
    "model_version": "version"
  }
}
```

指标阈值需要基于“噜噜短剧”的人工验收样本标定，不能把通用视觉相似度直接当成人类质量。

## 7. 质量评测

### 剧本与叙事

- 开头钩子和结尾钩子是否存在；
- 单集目标和冲突是否完成；
- 角色、关系、时间线和伏笔一致性；
- 台词是否符合固定角色语言风格；
- 改写是否破坏不可变设定。

### 视频可生产性

- 镜头生成成功率；
- 角色身份一致性；
- 长镜头 `identity_drift_curve` 与首末帧差异；
- 双角色 `instance_count_accuracy`、逐实例身份与异常主体率；
- 场景、服装和道具连续性；
- 提示词—画面一致度；
- 台词音频与镜头时长匹配率；
- 自动转写与目标台词的 WER；
- 角色音色相似度、情绪匹配与语音时长误差；
- 单集平均重试次数、成本和总耗时；
- 可复用素材比例。

## 7.1 固定角色语音方案

- MiniMax 自动填充语音保留为 baseline；主链路接入 IndexTTS-2.5，以授权参考音频固定噜噜/噜妹音色，并独立控制情绪和语速；
- 接入 Fun-CosyVoice 3.0 作为轻量备用和 A/B 对照；当每个角色积累约 1 分钟干净授权语音后，再评估 GPT-SoVITS 少样本微调；
- 为每个角色维护独立 Voice Card，保存音色参考池、情绪锚点、授权状态、语言及说话风格；
- 生成候选通过 ASR、说话人相似度、情绪、时长、响度/削波和人工盲听联合验收；
- 仅使用自己录制或获得授权的参考声音。模型/代码许可证与参考声音权利分开核验。

详细方案见 `VOICE_AND_CONSISTENCY_SPEC.md`。

### 最终成片

- 人工盲评胜率；
- 需要人工返工的镜头比例；
- 首次通过率；
- 若以后真实发布，再接入完播率、跳出点和互动反馈，但不在没有真实数据时伪造业务指标。

## 8. 数据飞轮

每次生产自动沉淀：

```text
剧本/分镜状态
+ 生成动作
+ 模型/参数/种子
+ 生成结果
+ 自动 QA
+ 人工接受/拒绝/修改
+ 成本和延迟
```

由此生成三类数据：

1. **成功模板库**：哪些角色、动作、景别和提示词组合最稳定；
2. **偏好数据**：同一镜头的多个版本，人工选择更好结果；
3. **Agent 轨迹**：从失败到修复的动作序列，用于 SFT 和 Agentic RL。

## 9. Agentic RL 的准确定位

不训练视频生成模型本身，而是训练 **生产编排策略**：面对一个剧本状态和生成反馈，决定下一步应该改提示词、换模板、拆镜头、改对白、复用素材还是停止。

状态：Production IR、当前生成结果、缺陷、历史尝试、资产库和预算。

动作：

- `revise_prompt`
- `switch_template`
- `split_shot`
- `rewrite_dialogue`
- `replace_with_voiceover`
- `reuse_asset`
- `regenerate`
- `accept_shot`
- `escalate_to_human`

奖励：

```text
R = 0.25 * accepted_shot
  + 0.20 * identity_consistency
  + 0.15 * prompt_alignment
  + 0.15 * continuity_score
  + 0.10 * audio_duration_fit
  + 0.10 * human_preference
  + 0.05 * asset_reuse
  - generation_cost
  - retry_penalty
  - hard_constraint_penalty
```

首版先做基于规则和历史成功率的 Recovery Policy；积累足够真实轨迹后，再用 veRL/verl-agent + GRPO。这样 RL 使用真实环境反馈，而不是为了简历硬塞算法。

## 10. 小作坊 MVP

### 必须做

- 噜噜短剧专属 `show_profile.yaml`；
- 角色、场景、道具和声音资产注册表；
- 剧本到 Production IR；
- 场景到分镜和生成任务；
- 一个可替换的视频后端 Adapter；
- 任务队列、重试、预算、检查点和断点恢复；
- 生成结果与镜头绑定；
- 人工接受/拒绝/修改；
- 版本 diff 和失败复盘页面。

### 暂时不做

- 通用短剧平台；
- 同时适配十几个视频模型；
- 从小说一键生成几十集；
- 端到端训练视频大模型；
- 没有数据支撑的爆款预测；
- 一开始就训练多智能体 RL。

## 11. 仓库建议

```text
lulu-studio-agent/
├── configs/lulu_show.yaml
├── assets/registry/
├── schemas/production_ir/
├── src/harness/
├── src/agents/
├── src/script/
├── src/storyboard/
├── src/video_adapters/
├── src/media_qa/
├── src/recovery/
├── src/evals/
├── training/sft/
├── training/grpo/
├── web/
├── tests/
└── examples/lulu_episode_001/
```

## 12. 对外表述

项目名称可用：

**LuluStudio Agent：面向固定 IP AI 短剧的剧本—分镜—视频联合生产与自优化系统**

完成 MVP 后的简历主线应是：

- 设计统一 Production IR，打通剧本、分镜、视频生成、配音和剪辑任务；
- 构建角色/场景资产记忆、镜头级状态持久化、生成重试和成本预算机制；
- 建立视频质量反馈驱动的 Recovery Planner，实现提示词、镜头和台词的局部自修复；
- 沉淀生成轨迹与人工偏好数据，并使用 GRPO 优化生产编排策略。
