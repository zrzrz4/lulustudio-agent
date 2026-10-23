# 噜噜短剧：角色一致性与双角色语音方案

## 1. 当前三个真实问题

1. 镜头持续时间变长后，噜噜的脸型、毛发、体型或服装逐渐漂移；
2. 同一画面出现两个相距较远的噜噜时，小主体容易失真、身份互相污染，画面还可能凭空生成第三个主体或奇怪道具；
3. MiniMax 自动填充语音虽然方便，但角色音色、情绪和台词时长缺少稳定、可复现的控制。

这三类问题都进入 Agent 的状态、评测和恢复动作，而不是继续只靠追加提示词。

## 2. 视频侧：长镜头不一致

### 2.1 生产策略

- 将长镜头拆为若干可独立验收的短片段；具体片段时长由真实 A/B 实验标定，不预设“最佳秒数”；
- 每个片段保存首帧、末帧、角色参考图、LoRA/视频参数、seed 和模型版本；
- 上一片段通过验收后，优先将其末帧作为下一片段的连续性参考；
- 相邻片段保留少量重叠帧，剪辑时在重叠区选择更稳定的切点；
- 按固定间隔抽帧计算身份漂移曲线，超过阈值时只重生成发生漂移的片段；
- 动作过大时优先拆动作或换景别，避免靠降低动作量获得“伪一致”。

### 2.2 评测字段

```text
identity_drift_curve[t]      各采样时刻与角色参考集的身份差异
fur_temporal_stability       毛发纹理是否闪烁、融化或改变方向
appearance_state_consistency 体型、服装、配饰是否保持
motion_amount_fit            动作幅度是否仍满足分镜
first_last_frame_gap         首末帧身份与场景状态差异
```

### 2.3 Agent 恢复动作

```text
split_shot
reuse_last_accepted_frame
reduce_motion_complexity
replace_transition_keyframe
switch_to_medium_or_close_shot
regenerate_failed_segment_only
```

## 3. 视频侧：两个远距离噜噜与异常物体

这里要区分 `character_identity` 和 `character_instance`。两个主体可以同属“噜噜”这个身份，但必须有不同实例 ID、空间区域和动作约束。

```yaml
character_instances:
  - instance_id: lulu_left
    identity_id: lulu
    reference_asset_id: lulu_ref_left
    region: left
    action: wave
  - instance_id: lulu_right
    identity_id: lulu
    reference_asset_id: lulu_ref_right
    region: right
    action: look_at_left
expected_instance_count: 2
forbid_extra_subjects: true
```

### 3.1 生成策略

- 不把“两个很小、相距很远、同时做复杂动作”的镜头作为默认模板；
- 剧情允许时，将全景交代镜头与中近景表演镜头拆开；
- 必须同框时，对左右主体分别使用参考裁剪、区域条件或 mask，明确位置、动作和道具归属；
- 单次直出不稳定时，分别生成左右角色层和背景，再合成后送入视频链路；
- 角色在画面占比过小时触发 `small_subject_risk`，改为更近景别或提高生成分辨率；
- 只修失败的角色层，避免另一个已经正确的噜噜在整镜头重生成时被破坏。

### 3.2 评测字段

```text
instance_count_accuracy      是否始终只有指定数量的角色
per_instance_identity        左右每个实例是否都像噜噜
instance_binding_accuracy    动作、位置、道具是否绑定到正确实例
spatial_relation_accuracy    左右/远近等关系是否符合分镜
extra_object_rate            未要求角色、肢体或道具的出现比例
small_subject_quality        小主体的脸型、轮廓和毛发可辨识度
```

当 `instance_count_accuracy` 或 `per_instance_identity` 不通过时直接拒绝，不允许被画面美学分抵消。

## 4. 语音后端选择

### 推荐组合

| 用途 | 模型 | 选择理由 | 注意事项 |
| --- | --- | --- | --- |
| 主后端 | IndexTTS-2.5 | 单参考音频零样本克隆；音色与情绪可分开控制；支持中文以及 `duration_factor` 语速/时长调整，适合短剧配音对齐 | 使用 bilibili Model Use License，发布或商业使用前检查模型协议与声音素材权利 |
| 备用/对照 | Fun-CosyVoice 3.0 0.5B | 中文与跨语言零样本克隆、情绪/语速/音量指令控制；模型和代码页面标注 Apache-2.0；0.5B 更适合小作坊部署 | 同样需要授权的参考音频；与主模型做盲听 A/B 后再定角色 |
| 有数据后的实验 | GPT-SoVITS | 5 秒零样本，约 1 分钟数据可少样本微调；带人声分离、切片、中文 ASR 和标注工具，适合固定角色数据整理 | 情绪控制不是当前强项；代码 MIT 不等于所有训练数据、参考声音自动获得商用权 |
| 仅研究对照 | F5-TTS | 易做零样本、多角色和微调实验 | 官方预训练模型为 CC-BY-NC，不作为商业发布默认方案 |

MiniMax 自动语音保留为 baseline，不再作为固定角色的唯一语音源。

## 5. 噜噜与噜妹的声音怎样“提取”

### 5.1 素材边界

只使用自己录制、明确授权或许可覆盖当前用途的声音。若“噜噜/噜妹”来源于第三方作品、配音演员或平台内置音色，不能因为技术上能克隆就默认拥有公开发布或商业使用权。更稳妥的方式是让自己或获授权的配音者录制原创角色声音，再固定成角色音色资产。

### 5.2 数据准备

每个角色建立独立 `Voice Card`：

```yaml
voice_id: lulu_voice_v1
speaker: lulu
authorized: true
reference_pool:
  neutral: [ref_neutral_01.wav, ref_neutral_02.wav]
  happy: [ref_happy_01.wav]
  sad: [ref_sad_01.wav]
  surprised: [ref_surprised_01.wav]
sample_rate: 24000
language: zh
style_notes: "温吞、憨萌、语速偏慢"
```

- 优先收集单人、无背景音乐、无音效、无混响的干净 WAV；
- 若只能从旧视频取声，先用 GPT-SoVITS 自带的 UVR5 工具做伴奏/人声分离，再用 VAD 切段、ASR 转写并人工筛选；
- 每段保留短而完整的一句话，剔除重叠说话、强噪声和严重失真的片段；
- 噜噜与噜妹分目录、分情绪保存，不把两个角色混在同一参考池；
- 零样本阶段先用少量高质量锚点；若稳定性仍不足，再为每个角色积累约 1 分钟干净授权语音做 GPT-SoVITS 少样本实验。

## 6. 语音 Agent 工作流

```text
台词 + 角色 + 情绪 + 目标镜头时长
        ↓
Voice Planner 选择 voice_id、参考音频和情绪控制
        ↓
IndexTTS-2.5 / CosyVoice 3 生成 2～3 个候选
        ↓
ASR 内容检查 + 说话人相似度 + 时长误差 + 音质检查
        ↓
人工 A/B 选择
        ↓
记录“输入—参数—输出—偏好—失败标签”
```

语音评测至少包含：

- `cer/wer`：生成台词是否正确；
- `speaker_similarity`：是否仍像对应角色；
- `emotion_match`：情绪是否符合分镜；
- `duration_error_ms`：是否落入镜头时长预算；
- `prosody_naturalness`：停顿、重音、语速是否自然；
- `noise/clipping/loudness`：噪声、削波和响度；
- `lip_sync`：仅在正脸且嘴部可见时计算。

失败恢复顺序：先改停顿/标点和发音标注，再换情绪参考或调整 `duration_factor`，仍不通过才拆台词或换语音后端。每次只改一个主要变量，以便生成可用于偏好学习的有效轨迹。

## 7. 可诚实写进项目的创新点

- 把长镜头角色漂移建模为随时间变化的质量曲线，并以片段级 checkpoint 局部回滚；
- 为同身份的多角色同框引入实例级绑定，联合检测角色数量、逐实例身份、空间关系与异常主体；
- 将语音纳入 Production IR 和 Agent 恢复闭环，而非生成结束后人工随意配音；
- 对视觉和语音都保存成对偏好与修复轨迹，后续可用于 SFT/GRPO 学习“遇到哪类失败应该采取什么动作”。
