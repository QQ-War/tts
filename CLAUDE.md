# CLAUDE.md

本仓库已迁移为 **Python + FastAPI** 的 Azure TTS 服务实现，旧的 Go 后端已移除。核心代码位于 `python_app/`，主要文件：
- `main.py`：FastAPI 路由与生命周期钩子
- `azure_tts.py`：与 Azure 语音服务交互的客户端
- `text_utils.py`：长文本切段工具
- `auth.py`：客户端 API Key 校验
- `config.py`：环境变量配置

容器相关文件：
- `python_app/Dockerfile`
- `docker-compose.yml`

如需前端或其他扩展，请根据需要新增实现，本文件不再维护旧的 Go 模块索引。
