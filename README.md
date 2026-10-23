# LuluStudio Agent

面向固定 IP“水豚噜噜”的短剧生产 Agent。项目重点不是封装一个聊天页面，而是建立可持久化的 Agent Harness：把分镜、关键帧、视频、配音、评测和失败恢复组织成可中断、可回滚、可积累经验的长周期任务。

## 当前 MVP

- `Episode → Scene → Shot → Attempt` 状态与 SQLite 持久化；
- Production IR：角色实例、动作、镜头、台词、音色、时长和预算约束；
- Tool Registry：统一封装 ComfyUI、视频、TTS 与评测工具；
- ComfyUI API 工作流提交、轮询与产物收集；
- Recovery Planner：根据缺陷、重试次数、历史成功率和成本选择局部恢复动作；
- 完整事件日志、人工 A/B 反馈和训练轨迹导出；
- FastAPI 控制面与 dry-run 演示后端。

## 架构

```text
Client / Script
      ↓
FastAPI Control Plane
      ↓
Persistent Agent Harness ─── SQLite event log / checkpoints
      ↓
Production IR → Tool Registry
                    ├── ComfyUI adapter
                    ├── MiniMax/video adapter
                    ├── IndexTTS/CosyVoice adapter
                    └── Media evaluator
      ↓
Recovery Planner → local retry / rollback / human review
```

## 快速启动

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
lulu-agent init-db
lulu-agent serve --host 0.0.0.0 --port 8010
```

Windows PowerShell 激活命令为 `.venv\Scripts\Activate.ps1`。

健康检查：

```bash
curl http://127.0.0.1:8010/health
```

AutoDL 后台运行可直接使用：

```bash
bash scripts/autodl_start.sh
bash scripts/smoke_test.sh
```

创建演示任务：

```bash
curl -X POST http://127.0.0.1:8010/episodes/demo \
  -H 'Content-Type: application/json' \
  -d @examples/demo_episode.json

curl -X POST http://127.0.0.1:8010/episodes/demo/run
```

默认 `LULU_DRY_RUN=true`，不会消耗真实模型额度。切换真实 ComfyUI 前，需要导出 API-format workflow JSON，放入 `workflows/`，再把 `LULU_DRY_RUN=false`。

## AutoDL 部署建议

- 代码、数据库与大体积实验产物放在 `/root/autodl-tmp/lulustudio-agent`；
- ComfyUI 继续使用 `/root/ComfyUI` 和端口 `6006`；
- Agent API 使用 `8010`；
- TTS 单独进程/虚拟环境运行，避免与 ComfyUI 的 CUDA、Torch 依赖冲突；
- 单 GPU 时按工具队列串行加载模型，不让 FLUX、视频和 TTS 同时占用显存。

## 真实后端接入

### ComfyUI

`ComfyUITool` 读取 API-format workflow JSON，并将其中形如 `{{PROMPT}}`、`{{SEED}}` 的占位符替换为调用参数，然后提交 `/prompt`，轮询 `/history/{prompt_id}`。

### MiniMax 与 TTS

通过 HTTP Sidecar 接入。Agent 只依赖统一的 `/generate` 请求和结构化返回，不把第三方 SDK 绑定进核心状态机。

## 数据与安全

- `.env`、API Key、SSH密码、授权语音和模型权重不提交 Git；
- GitHub只保存代码、配置模板、工作流空壳、hash与少量可公开样例；
- 声音克隆只使用自己录制或明确授权的参考素材；
- GRPO未训练完成前，不在简历中写“完成强化学习优化”。

完整项目经历与设计见：

- `AGENT_PROJECT_EXPERIENCE.md`
- `LULU_DRAMA_AGENT_SPEC.md`
- `EVALUATION_EVOLUTION_SPEC.md`
- `VOICE_AND_CONSISTENCY_SPEC.md`
