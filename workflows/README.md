# Workflows

将 ComfyUI 导出的 **API-format JSON** 放在这里。普通 UI workflow JSON 不能直接提交 `/prompt`。

支持以下完整字符串占位符：

- `{{PROMPT}}`
- `{{SEED}}`
- `{{DURATION_MS}}`
- `ShotSpec.parameters` 中的任意同名键

不要提交模型权重、API Key、绝对私有路径或包含未授权素材的工作流。
