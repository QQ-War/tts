# Azure TTS 服务（Python 版）

这是一个基于 Microsoft Azure 语音服务的文本转语音 (TTS) 服务，使用 **Python + FastAPI** 实现，支持长文本自动切分、可选流式音频返回以及客户端 API Key 校验。所有配置统一从 `config.yaml` 读取，便于部署与管理。

## ✨ 主要特性
- 纯 Azure 语音服务调用，支持语音列表和文本转语音接口。
- 智能分段：按标点和长度自动切段以处理长文本。
- 流式传输：可配置的分片音频返回，减少播放卡顿。
- 可选鉴权：通过 `TTS_API_KEY` 校验客户端请求。
- 容器化：提供 Dockerfile 与 docker-compose 快速部署。

## 🚀 快速开始

### 本地运行（Python）
```shell
# 安装依赖
cd python_app
pip install -r requirements.txt

# 在项目根目录配置 config.yaml（示例见下文）
# 如需避免将密钥写入文件，可通过环境变量覆盖：
#   export AZURE_TTS_KEY=你的AzureKey
#   export AZURE_TTS_REGION=你的Region

# 启动服务（默认端口 8000，可通过 TTS_CONFIG_PATH 指定配置文件路径）
uvicorn python_app.main:app --reload
```

### Docker / Compose
```shell
# 启动后端（默认读取仓库根目录的 config.yaml）
docker-compose up --build

# 单独构建运行后端镜像
docker build -t azure-tts -f python_app/Dockerfile .
docker run -p 8000:8000 \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -e TTS_CONFIG_PATH=/app/config.yaml \
  azure-tts
```

## ⚙️ 配置

所有配置集中在仓库根目录的 `config.yaml`（支持 YAML/JSON），可通过环境变量 `TTS_CONFIG_PATH` 指向自定义路径。`AZURE_TTS_KEY` 与 `AZURE_TTS_REGION` 可使用环境变量覆盖，以便在生产环境中避免将密钥写入文件。

```yaml
azure:
  key: YOUR_AZURE_KEY            # 必填，可被环境变量 AZURE_TTS_KEY 覆盖
  region: YOUR_AZURE_REGION      # 必填，可被环境变量 AZURE_TTS_REGION 覆盖

auth:
  api_key: YOUR_API_KEY          # 为空则关闭客户端鉴权

defaults:
  voice: zh-CN-XiaoxiaoNeural
  style: general
  rate: "+0%"
  pitch: "+0%"
  output_format: audio-24khz-160kbitrate-mono-mp3
  max_text_length: 4500
  segment_length: 300
  enable_streaming: false
```

> 如果更偏好 JSON 格式，`config.yaml` 也支持 JSON 内容。

## 📚 API

所有接口均位于 `/api/v1/`，支持通过以下任一方式提供 `TTS_API_KEY`（若已配置）：
- `Authorization: Bearer <api_key>`
- 查询参数 `?api_key=...`

### 健康检查
```shell
GET /api/v1/health
```

### 获取可用语音
```shell
GET /api/v1/voices[?locale=en-US]
```

### 文本转语音
```shell
# GET，流式可通过 query 开启
GET /api/v1/tts?t=你好世界&voice=zh-CN-XiaoxiaoNeural&stream=true

# POST，支持更多参数
POST /api/v1/tts
{
  "text": "你好世界",
  "voice": "zh-CN-XiaoxiaoNeural",
  "style": "general",
  "rate": "+0%",
  "pitch": "+0%",
  "stream": true
}
```

### 获取运行配置
```shell
GET /api/v1/config
```

## 🧪 开发与测试
```shell
python -m pytest python_app
```

> 说明：仓库已移除旧的 Go 后端，仅保留 Python 实现与相关容器配置。
