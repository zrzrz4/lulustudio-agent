# Workflows

将 ComfyUI 导出的 **API-format JSON** 放在这里。普通 UI workflow JSON 不能直接提交 `/prompt`。

支持以下完整字符串占位符：

- `{{PROMPT}}`
- `{{SEED}}`
- `{{DURATION_MS}}`
- `ShotSpec.parameters` 中的任意同名键

不要提交模型权重、API Key、绝对私有路径或包含未授权素材的工作流。

`flux_lulu_t2i_api.json` 是首个可执行基线：使用 FLUX.1-dev FP8 单文件检查点、噜噜 LoRA 和 Euler/simple 25 步采样生成角色定帧。运行参数由 Episode JSON 注入，模型权重和私人参考素材不进入 Git。

AutoDL 上可运行 `bash scripts/run_flux_baseline.sh`：脚本会校验检查点和 ComfyUI、以非 dry-run 模式启动独立 Agent，并执行 `examples/flux_lulu_baseline.json`。健康检查、创建结果和最终轨迹分别保存在 `logs/`，便于复现实验与归因。
