# Azure TTS 服务（Python 版）

这是一个基于 Microsoft Azure 语音服务的文本转语音 (TTS) 服务，使用 **Python + FastAPI** 实现，支持长文本自动切分、可选流式音频返回以及客户端 API Key 校验。

## ✨ 主要特性
- 纯 Azure 语音服务调用，支持语音列表和文本转语音接口。
- 智能分段：按标点和长度自动切段以处理长文本。
- 流式传输：可配置的分片音频返回，减少播放卡顿。
- 可选鉴权：通过 `TTS_API_KEY` 校验客户端请求。
- 容器化：提供 Dockerfile 与 docker-compose 快速部署。

## 🚀 快速开始

### 本地运行（Python）
```shell
cd python_app
pip install -r requirements.txt

# 设置 Azure 凭据与可选客户端 API Key
export AZURE_TTS_KEY=你的AzureKey
export AZURE_TTS_REGION=你的Region
export TTS_API_KEY=YOUR_API_KEY  # 可选，但建议开启

# 可选：自定义默认参数
export TTS_DEFAULT_VOICE=zh-CN-XiaoxiaoNeural
export TTS_SEGMENT_LENGTH=300
export TTS_ENABLE_STREAMING=true  # 默认开启流式

# 启动服务（默认端口 8000）
uvicorn python_app.main:app --reload
```

### Docker / Compose
```shell
# 仅启动 Azure TTS Python 服务
docker-compose up --build azure-tts

# 或使用镜像直接运行
cd python_app
docker build -t azure-tts .
docker run -p 8000:8000 \
  -e AZURE_TTS_KEY=你的AzureKey \
  -e AZURE_TTS_REGION=你的Region \
  -e TTS_API_KEY=YOUR_API_KEY \
  azure-tts
```

## ⚙️ 配置

环境变量 | 说明 | 默认值
---|---|---
`AZURE_TTS_KEY` | Azure 语音服务密钥 | 必填
`AZURE_TTS_REGION` | Azure 区域，例如 `eastasia` | 必填
`TTS_API_KEY` | 客户端访问校验用 Key | 空（不校验）
`TTS_DEFAULT_VOICE` | 默认语音 | `zh-CN-XiaoxiaoNeural`
`TTS_DEFAULT_STYLE` | 默认风格 | `general`
`TTS_DEFAULT_RATE` | 默认语速 | `+0%`
`TTS_DEFAULT_PITCH` | 默认语调 | `+0%`
`TTS_OUTPUT_FORMAT` | 音频格式 | `audio-24khz-160kbitrate-mono-mp3`
`TTS_MAX_TEXT_LENGTH` | 单次文本长度上限 | `4500`
`TTS_SEGMENT_LENGTH` | 自动切段阈值 | `300`
`TTS_ENABLE_STREAMING` | 默认是否流式返回 | `false`

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
