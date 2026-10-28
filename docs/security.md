# Environment configuration / 环境配置

The bundled demonstration runs without API credentials. Optional model-backed retrieval reads `MIMO_API_KEY`, `GEMINI_API_KEY` and `DEEPSEEK_API_KEY` from the backend environment. Keep provider keys on the backend; frontend configuration contains only public URLs.

内置演示无需 API 密钥。启用模型检索时，在后端环境中配置所选服务的密钥；前端只配置可公开的服务地址。

## Local setup

```bash
cp .env.example .env
```

Fill in the supported variables in your local `.env`. The file is ignored by Git; keep the committed template's credential fields empty. For entrypoints that read process variables, add `--env-file .env` to the documented `uv run` command. See the repository's running guide for provider and data options.

在本地 `.env` 中填写所需变量，提交的示例文件保持空白。读取进程环境变量的入口可通过 `uv run --env-file .env ...` 载入配置，具体运行方式见对应说明。

## Repository check

With [Gitleaks](https://github.com/gitleaks/gitleaks) installed and on PATH:

```bash
uv run python scripts/check_secrets.py --history
```

This checks publication files and reachable Git history using the repository's detector configuration. Reports show locations without credential values.
