# Lulu-Eval：噜噜短剧评测与持续进化方案

## 1. 核心原则

Agent 能否持续进化，取决于评测系统能不能稳定回答三个问题：

1. 当前镜头/整集是否可以交付？
2. 这次动作相对上一次是否真的改善？
3. 改善是否值得付出的生成成本和时间？

评测系统不追求一个万能总分，而采用：

```text
硬门槛 Gate
+ 分维度自动指标
+ 噜噜短剧人工偏好
+ 生产成本
= 可训练 Reward
```

其中自动指标必须经过“噜噜短剧”人工样本校准。通用模型给出的 CLIP、VLM 或美学分只能作为候选特征，不能直接等于质量。

## 2. 三层评测对象

### Level 1：镜头级 Shot Eval

判断一个 3～10 秒生成镜头是否可用，以及哪里有问题。

### Level 2：场景/整集 Episode Eval

判断多个镜头拼接后是否连续、叙事清楚、节奏合理，不能用单镜头高分代替。

### Level 3：Agent Trajectory Eval

判断 Agent 面对失败镜头时，是否以较少重试和较低成本采取了正确恢复动作。

三层分开存储、分开奖励，避免镜头漂亮但故事不通，或者最终成功却浪费大量生成次数。

## 3. 镜头级评测标准

### 3.1 硬门槛：不满足就直接拒绝

| 类别 | 检查方式 | 结果 |
| --- | --- | --- |
| 文件有效 | 可解码、帧数/FPS/分辨率正确 | pass/fail |
| 时长 | 与 Production IR 的目标时长误差在容许范围 | pass/fail |
| 主体存在 | 指定角色/主体在要求的时间段出现 | pass/fail |
| 锁定约束 | 固定服装、关键道具、角色数量等 | pass/fail |
| 音频有效 | 无静音、削波、缺失，目标对白可识别 | pass/fail |
| 安全约束 | 命中禁止内容或不适合发布的元素 | pass/fail |

硬门槛不使用加权平均。关键角色缺失时，即使画质和美学分很高，也不能被其他指标补偿。

### 3.2 角色与视觉一致性

- `identity_similarity`：采样角色区域与噜噜角色参考集的嵌入相似度；
- `intra_shot_identity_stability`：同一镜头不同帧的身份漂移；
- `identity_drift_curve`：长镜头按时间采样，观察身份质量从何时开始持续下降；
- `first_last_frame_gap`：首末帧角色身份和外观状态差异；
- `instance_count_accuracy`：双角色镜头是否始终保持指定数量；
- `per_instance_identity`：左右每个角色实例分别与参考集比较，避免整图高分掩盖其中一个失败；
- `extra_object_rate`：额外角色、肢体或未要求道具的出现比例；
- `costume_consistency`：服装颜色、款式、配饰是否符合当前场景状态；
- `prop_consistency`：关键道具是否存在、归属和状态是否正确；
- `background_consistency`：场景布局和关键元素是否稳定；
- `artifact_severity`：手、脸、文字、遮挡、局部融化、重复肢体等错误等级。

角色参考不能只有一张图，至少按正面、侧面、半身、全身、不同表情建立 reference bank，按对应镜头类型比较。

### 3.3 提示词与动作实现

- 人物、数量、属性是否绑定到正确对象；
- 同一身份的多个实例是否具有独立 ID，位置、动作和道具是否正确绑定；
- 动作主体和动作对象是否正确；
- 空间关系是否正确；
- 镜头景别、机位和运镜是否实现；
- 关键事件是否在指定时间段发生；
- 是否错误生成提示词中没有要求的主体。

检测器/跟踪器负责“有几个、在哪里、谁在移动”，多模态模型负责难以规则化的动作语义。二者结果冲突时进入人工抽检，而不是让 VLM 一票决定。

### 3.4 时间质量与运动质量

- `flicker`：亮度、纹理或局部结构的异常闪烁；
- `motion_smoothness`：光流或关键点轨迹是否突跳；
- `motion_amount_fit`：运动幅度是否符合分镜要求；
- `static_cheating`：要求明显动作时，视频是否用近似静帧骗取一致性高分；
- `camera_motion_fit`：镜头运动方向与强度是否符合 Production IR；
- `temporal_artifact`：主体消失、变形、穿模或背景突然替换。

时间一致性与运动幅度必须联用：只奖励相邻帧相似会诱导 Agent 选择静止镜头。

### 3.5 音频与口型

- `asr_wer`：将生成音频转写后与目标台词比较；
- `speech_duration_error`：台词时长与分镜预算之差；
- `lip_sync_confidence/distance`：对说话镜头计算 SyncNet 类 LSE-C/LSE-D；
- `voice_identity`：说话人音色是否匹配角色；
- `emotion_match`：语音情绪是否符合分镜和台词；
- `prosody_naturalness`：停顿、重音和语速是否自然；
- `loudness/noise/clipping`：响度、底噪与削波；
- `subtitle_alignment`：字幕内容和时间戳是否对齐。

口型指标只用于可见嘴部且真实发声的镜头；背影、画外音、遮挡镜头不应被错误扣分。

语音模型以 MiniMax 自动语音为 baseline，IndexTTS-2.5 为主后端，Fun-CosyVoice 3.0 为备用。每条台词保留模型版本、`voice_id`、参考音频、情绪控制、语速/时长参数和人工 A/B 结果，避免只保存最终 wav 而无法复现。

## 4. 场景与整集评测

### 4.1 连续性

- 前一镜头末帧与后一镜头首帧的人物、服装、道具和地点状态；
- 人物出入场方向和视线方向；
- Story Bible 中关系、知识边界和时间线是否被破坏；
- 动作是否衔接，例如上一镜头已经放下道具，下一镜头不能仍持有；
- 角色音色、字幕样式、画风和色调是否突变。

### 4.2 叙事完成度

- 开场钩子是否在时间预算内出现；
- 本集冲突是否建立并推进；
- 每个场景是否产生新信息或状态变化；
- 因果链是否可由成片理解，而不依赖剧本文字；
- 结尾钩子是否成立；
- 关键台词和关键画面是否都出现在剪辑时间线。

### 4.3 节奏与可看性

- 镜头时长分布；
- 连续相似景别或静态镜头比例；
- 对白密度、无信息停顿和字幕阅读时间；
- 音乐、对白和音效是否抢占；
- 单集总时长、预算和返工量。

叙事与可看性先采用结构化 rubric 的 A/B 盲评，不用单个 LLM 的 0～100 绝对分做真值。

## 5. 如何生成“噜噜短剧”自己的标准

### 5.1 建立失败分类表

先从过去 ComfyUI 生产结果中抽取真实 bad cases，不从论文指标倒推业务：

```text
character_drift
wrong_character_count
costume_or_prop_error
scene_drift
action_not_executed
prompt_misalignment
motion_jitter
static_cheating
lip_sync_error
dialogue_too_long
shot_transition_break
narrative_missing_information
generation_timeout_or_oom
excessive_retry
```

每个类别定义：可观察现象、严重等级、自动检测候选、允许的恢复动作和最终验收规则。

### 5.2 构建人工锚点集

首版建议从已有结果中整理 150～300 组 A/B 镜头对，而不是让你给几千条视频逐个打分：

- A/B 来自同一分镜、同一角色资产的不同参数或不同恢复方案；
- 隐藏模型、参数、成本和文件名，随机左右顺序；
- 标注 `A更好 / B更好 / 持平 / 两个都拒绝`；
- 同时选择主要失败标签，不要求写长理由；
- 约 20% 样本重复出现，用来检查标注稳定性；
- 每类重要缺陷都保留“明确通过、临界、明确失败”的 anchor；
- 单独冻结一份 gold set，永不参与奖励模型训练。

小作坊可以先由你作为主标注者，再找另一人只复核临界样本；这样比多人给绝对分更省成本。

### 5.3 校准自动指标

对每个候选指标计算：

- 与人工 A/B 选择的一致率；
- Spearman 相关或 Kendall 排序相关；
- 各失败类型上的 Precision / Recall；
- 不同镜头类型、角色、场景和视频长度上的稳定性；
- 阈值附近的假通过与假拒绝案例。

只有达到预先设定门槛的指标才进入自动 Gate 或 Reward。表现一般的指标保留为诊断信息；与人工偏好持续冲突的指标移除。

### 5.4 版本化

```text
lulu-eval-v0.1
├── rubric.yaml
├── failure_taxonomy.yaml
├── metric_config.yaml
├── thresholds.yaml
├── anchors/
├── gold_set.jsonl
└── changelog.md
```

修改角色设定、工作流或生成模型后，不覆盖旧标准，而是发布新版本并在同一 gold set 上回归测试。

## 6. 不要直接用一个加权总分

建议使用“门控 + 几何/调和聚合 + 偏好”的方式：

```text
if hard_gate_failed:
    quality = 0
else:
    quality = geometric_mean(
        identity,
        prompt_alignment,
        temporal_quality,
        audio_fit,
        continuity
    )
```

几何均值会惩罚明显短板，避免 0.2 的角色一致性被 0.95 的画面美学分抵消。美学和人工偏好作为排序信号，不覆盖硬失败。

## 7. Agent Reward：奖励“改进量”而不是绝对质量

Agent 的一步动作应按前后差值计分：

```text
r_step = clip(Q_after - Q_before, -1, 1)
       - lambda_cost * normalized_generation_cost
       - lambda_retry * retry_count
       - invalid_action_penalty
```

终局奖励：

```text
r_terminal = accepted_by_human_or_gate
           + episode_continuity
           + human_pairwise_preference
           - total_cost
           - unnecessary_script_change
```

这样一个原本很差但被 Agent 成功修好的镜头能获得合理奖励；一个本来就很好的镜头被无意义重生成，则会因改进量低和成本增加受到惩罚。

## 8. GRPO 任务构造

训练样本不是“给一个剧本写视频提示词”，而是一个真实失败状态：

```text
输入：
  Production IR
  + 当前视频及评测报告
  + 历史尝试
  + 可用资产
  + 剩余预算

输出动作：
  revise_prompt / switch_template / split_shot /
  rewrite_dialogue / reuse_asset / regenerate /
  accept / escalate_to_human
```

对同一个失败状态采样 4～8 条恢复轨迹，按最终改进量、通过率和成本排序，用 GRPO 计算组内相对优势。视频生成结果和评测报告属于环境 observation，不对这些 token 计算 loss。

训练前至少要有：

- 一套稳定的 Lulu-Eval 版本；
- 可复现的 ComfyUI workflow 和随机种子记录；
- 足够的成功/失败恢复轨迹；
- 冻结测试集；
- 不依赖 RL 也能工作的规则 Recovery Policy。

## 9. 持续进化闭环

```text
生产生成候选
   ↓
硬门槛 + 自动分维度评测
   ↓
高置信通过/拒绝直接处理
   ↓
只把高价值样本交给人工
   ├── 自动指标互相冲突
   ├── 接近验收阈值
   ├── Reward Model 不确定
   ├── 新失败类型
   └── Agent 高成本仍未解决
   ↓
形成 A/B 偏好与失败标签
   ↓
更新评测器/Reward Model
   ↓
先 shadow test，再小流量启用
   ↓
SFT 成功轨迹 → GRPO 恢复策略
```

不是每生成一个镜头就在线更新模型。建议按数据批次更新，并保留 evaluator、policy、ComfyUI workflow 和视频模型四类版本，支持回滚。

## 10. 防止“越训越歪”

- 训练集、调参集、gold set 严格隔离；
- Judge 不查看哪个候选来自哪个模型或 Agent；
- A/B 左右位置随机；
- 自动分数不能覆盖人工明确拒绝；
- 记录评测器与人工冲突的案例，不只记录平均分；
- 定期加入静帧、高相似但无动作、过度磨皮等对抗样本；
- 对模型新版本做旧 gold set 回归；
- Reward Model 只做排序和辅助，不成为唯一发布门槛；
- 评测器升级后先离线重放历史轨迹，检查策略排名是否异常翻转。

## 11. 最小可落地顺序

1. 把旧 ComfyUI 生成记录统一成 `generation_run.json`；
2. 整理 50 个典型失败镜头和失败分类表；
3. 做 A/B 标注页面和 150～300 组锚点集；
4. 先实现文件、时长、主体、身份、运动、ASR、成本等基础 evaluator；
5. 用锚点集校准阈值，发布 `lulu-eval-v0.1`；
6. 实现不训练的规则 Recovery Planner；
7. 持续保存“状态—动作—新结果—奖励”轨迹；
8. 先对成功轨迹做 SFT，再在云端做 GRPO；
9. 使用冻结 gold set 比较规则、SFT 和 GRPO 的通过率、成本和人工胜率。

这个顺序中，评测和数据先于 RL。没有经过人工校准的评测器，无法产生可信奖励。
