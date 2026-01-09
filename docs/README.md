# libre-converter-api

基于 LibreOffice 的生产级文档转换 API 服务，打包为最小化 Docker 容器，支持多进程异步处理。

## 特性

- **多格式支持**：DOC、DOCX、XLS、XLSX、PPT、PPTX、PDF、ODF、CSV、RTF、HTML、TXT
- **中文字体支持**：内置 27 款中文字体，完美渲染中文
- **多架构支持**：同时支持 `linux/amd64` 和 `linux/arm64`（Apple Silicon）
- **生产就绪**：Gunicorn + Uvicorn 多进程、JSON 日志、性能指标
- **可选认证**：通过环境变量控制 Bearer Token 认证
- **资源限制**：可配置文件大小、并发数、超时时间

## 快速开始

### 使用 Docker Compose（推荐）

```bash
# 克隆仓库
git clone https://github.com/Quantatirsk/libre-converter-api.git
cd libre-converter-api

# 配置环境变量
cp .env.example .env
# 根据需要编辑 .env

# 启动服务
docker-compose up -d
```

### 使用 Docker

```bash
# 无认证运行
docker run -d -p 28001:28001 quantatrisk/libre-converter-api:latest

# 启用认证运行
docker run -d -p 28001:28001 \
  -e API_AUTH_ENABLED=true \
  -e API_AUTH_TOKEN=your-secret-token \
  quantatrisk/libre-converter-api:latest
```

## API 使用

### 健康检查

```bash
curl http://localhost:28001/health
```

### 查看支持的格式

```bash
curl http://localhost:28001/formats
```

### 转换文档

```bash
# DOCX 转 PDF
curl -X POST "http://localhost:28001/convert?to=pdf" \
  -F "file=@document.docx" \
  -o document.pdf

# 带认证
curl -X POST "http://localhost:28001/convert?to=pdf" \
  -H "Authorization: Bearer your-token" \
  -F "file=@document.docx" \
  -o document.pdf
```

## 支持的转换格式

| 输入格式 | 可转换为 |
|---------|---------|
| doc, docx, odt, rtf | doc, docx, pdf, odt, txt, rtf, html |
| xls, xlsx, ods, csv | xls, xlsx, pdf, ods, csv |
| ppt, pptx, odp | ppt, pptx, pdf, odp |

## 配置项

| 变量 | 默认值 | 说明 |
|-----|-------|------|
| `API_AUTH_ENABLED` | `false` | 启用 Bearer Token 认证 |
| `API_AUTH_TOKEN` | `""` | 认证密钥 |
| `API_PORT` | `28001` | 服务端口 |
| `API_WORKERS` | `auto` | 工作进程数（auto = CPU 核数） |
| `API_TIMEOUT` | `300` | 请求超时时间（秒） |
| `API_MAX_FILE_SIZE` | `524288000` | 最大上传文件大小（500MB） |
| `API_MAX_CONCURRENT` | `10` | 最大并发转换数 |
| `LOG_LEVEL` | `info` | 日志级别 |
| `LOG_FORMAT` | `json` | 日志格式 |

## 构建镜像

```bash
# 构建并推送多架构镜像
./build.sh

# 指定版本标签
./build.sh v1.0.0
```

## 文档

- [设计文档](DESIGN.md) - 架构与设计决策
- [部署指南](DEPLOYMENT.md) - 详细部署说明

## 许可证

MIT
