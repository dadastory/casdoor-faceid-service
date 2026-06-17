# Casdoor Face ID Service

<div align="center">
  <h3>基于 UniFace 的 Casdoor 本地 Face ID 服务</h3>

  <p>
    <strong>用于 Casdoor 本地人脸登录的无状态 Python 人脸分析服务。</strong><br>
    人脸检测、人脸识别、活体检测和人脸解析能力由
    <a href="https://github.com/yakhyo/uniface">UniFace</a> 提供。
  </p>

  <p>
    <a href="README.md"><strong>English</strong></a>
  </p>

  <p>
    <a href="./LICENSE">
      <img src="https://img.shields.io/badge/license-Apache--2.0-orange?style=flat-square" alt="License">
    </a>
    <a href="https://github.com/astral-sh/uv">
      <img src="https://img.shields.io/badge/dependencies-uv-654ff0?style=flat-square" alt="uv">
    </a>
  </p>
</div>

---

## 目录

- [项目作用](#项目作用)
- [实现原理](#实现原理)
- [功能特性](#功能特性)
- [环境要求](#环境要求)
- [快速开始](#快速开始)
- [Casdoor 对接](#casdoor-对接)
- [用户录入人脸](#用户录入人脸)
- [配置项](#配置项)
- [模型下载和国内镜像](#模型下载和国内镜像)
- [API](#api)
- [常见问题](#常见问题)
- [安全建议](#安全建议)
- [许可证](#许可证)
- [Star History](#star-history)

## 项目作用

Casdoor Face ID Service 是给 Casdoor 本地人脸登录使用的 Python 服务。它适用于包含 `Local UniFace` Face ID Provider 的 Casdoor fork，让 Casdoor 可以在不依赖阿里云 Facebody 的情况下提供 Face ID 登录。

这个服务是无状态的：

- 不保存用户。
- 不保存注册人脸图片。
- 不保存人脸向量或管理记录。
- 用户、人脸数据、上传资源、Provider 配置和删除逻辑仍由 Casdoor 管理。

## 实现原理

登录流程如下：

```text
浏览器
  | 1. 采集登录人脸图片
  v
Casdoor
  | 2. 从用户资料读取 user.faceIds[].imageUrl
  | 3. 通过 Casdoor Storage 下载已注册人脸图片
  | 4. 把两张图片发送到 POST /v1/compare
  v
casdoor-faceid-service
  | 5. 对登录图片做活体检测
  | 6. 检测两张图片中的单个人脸
  | 7. 提取归一化人脸特征向量
  | 8. 计算相似度并返回 matched=true/false
  v
Casdoor 登录结果
```

当前只对登录图片做活体检测。已注册图片属于 Casdoor 管理的用户资料。

服务内部使用官方 [UniFace](https://github.com/yakhyo/uniface) Python 库：

- 人脸检测：默认 `RetinaFace`。
- 人脸识别：默认 `ArcFace`。
- 反欺骗：开启活体检测时使用 `MiniFASNet`。
- 人脸解析：默认 `BiSeNet`。
- 推理后端：ONNX Runtime CPU 或 CUDA Provider。

## 功能特性

| 模块 | 支持情况 |
|------|----------|
| 人脸检测 | 默认 RetinaFace；可选 SCRFD、YOLOv5Face、YOLOv8Face |
| 人脸识别 | 默认 ArcFace；可选 AdaFace、EdgeFace、MobileFace、SphereFace |
| 活体检测 | 默认开启，使用 MiniFASNet 反欺骗 |
| 人脸解析 | 默认 BiSeNet；可选 XSeg |
| 运行方式 | CPU 和 GPU 两个 Docker Compose profile |
| GPU | ONNX Runtime CUDA Provider，失败时可回退 CPU |
| 安全 | `/v1/*` 接口可启用 Bearer Token |
| 部署 | Docker、Docker Compose、uv 依赖管理、国内镜像源和 GitHub 代理 |

## 环境要求

CPU 运行：

- Docker 和 Docker Compose v2。

GPU 运行：

- 宿主机已安装 NVIDIA 驱动。
- 已安装 NVIDIA Container Toolkit。
- GPU 镜像需要包含 CUDA 12 和 cuDNN 9 运行库，默认使用 `nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04`。

## 快速开始

创建本地配置：

```bash
cp .env.example .env
```

CPU 启动：

```bash
docker compose --profile cpu up -d --build faceid-cpu --build
```

GPU 启动：

```bash
docker compose --profile gpu up -d --build faceid-gpu --build
```

检查服务状态：

```bash
curl http://127.0.0.1:8100/health
```

正常会看到：

```json
{
  "status": "ok",
  "service": "casdoor-faceid-service",
  "device": "cpu",
  "livenessEnabled": true
}
```

### 指定 GPU

使用所有可见 GPU：

```bash
FACEID_GPU_DEVICES=all docker compose --profile gpu up -d faceid-gpu
```

使用第 0 张卡：

```bash
FACEID_GPU_DEVICES=0 docker compose --profile gpu up -d faceid-gpu
```

使用多张卡：

```bash
FACEID_GPU_DEVICES=0,1 docker compose --profile gpu up -d faceid-gpu
```

当前服务仍是单进程，多卡配置主要用于控制 ONNX Runtime 可见设备。

## Casdoor 对接

Casdoor 需要包含 `Local UniFace` Face ID Provider 的 fork 版本。

在 Casdoor 中创建或修改 Provider：

```text
Category: Face ID
Type: Local UniFace
Endpoint: http://172.17.0.1:8100
Client secret: <与 FACEID_API_KEY 一致，本地开发可留空>
```

如果 Casdoor 和本服务在同一个 Docker Compose 网络，可以使用服务名：

```text
Endpoint: http://faceid-cpu:8100
```

如果 Casdoor 运行在 Docker 中，而本服务把 `8100` 端口发布到宿主机，需要使用 Casdoor 容器能访问到的地址：

```text
Endpoint: http://172.17.0.1:8100
```

`Local UniFace` 不需要配置阿里云密钥，只需要 `Endpoint` 和可选的 `Client secret`。

## 用户录入人脸

Casdoor 会把已录入人脸信息保存在用户对象里：

```json
{
  "faceIds": [
    {
      "name": "face-main",
      "imageUrl": "http://casdoor.example.com/files/resource/org/alice/face.jpg",
      "faceIdData": []
    }
  ]
}
```

图片先通过 Casdoor Resource/Storage 上传，然后把返回 URL 写入 `faceIds[].imageUrl`。

用户自助录入流程：

1. 用户先用密码、验证码、OAuth 等非 Face ID 方式登录。
2. 用户打开 Casdoor `/account`。
3. 组织的 Account items 中 `Face ID` 必须允许 `Self` 查看和修改。
4. 用户上传图片或拍照添加 Face ID。
5. 后续登录可以选择 Face ID。

业务应用可以在自己的账号设置页增加入口：

```text
https://<casdoor-host>/account
```

### Local Storage 注意事项

Local File System 类型的 Storage 会按下面格式生成文件 URL：

```text
<Domain>/files/<objectKey>
```

Casdoor 后端必须能访问 `faceIds[].imageUrl` 中保存的 URL。如果 Casdoor 在 Docker 容器里运行，不要保存容器内无法访问的 `http://127.0.0.1:8000/files/...`。

本地 Docker 部署常见配置是：

```text
http://172.17.0.1:18000
```

如果后续修改 Storage Provider 的 `Domain`，老用户的 `faceIds[].imageUrl` 可能仍指向旧地址。建议保持域名稳定，或者批量更新用户数据。

## 配置项

复制 `.env.example` 为 `.env` 后按需修改。

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `FACEID_PORT` | `8100` | Docker Compose 发布到宿主机的端口 |
| `FACEID_API_KEY` | 空 | `/v1/*` 接口 Bearer Token |
| `FACEID_ENABLE_LIVENESS` | `true` | 比对时启用活体检测 |
| `FACEID_SIMILARITY_THRESHOLD` | `0.6` | 人脸匹配最低相似度 |
| `FACEID_LIVENESS_THRESHOLD` | `0.7` | 活体检测最低置信度 |
| `FACEID_DETECTOR` | `retinaface` | `retinaface`、`scrfd`、`yolov5` 或 `yolov8` |
| `FACEID_RECOGNIZER` | `arcface` | `arcface`、`adaface`、`edgeface`、`mobileface` 或 `sphereface` |
| `FACEID_PARSER` | `bisenet` | `bisenet` 或 `xseg` |
| `FACEID_MAX_IMAGE_BYTES` | `8388608` | 最大图片大小 |
| `FACEID_PRELOAD_MODE` | `all` | `all`、`core` 或 `none` |
| `FACEID_CPU_BASE_IMAGE` | `python:3.11-slim` | CPU 基础镜像 |
| `FACEID_GPU_BASE_IMAGE` | `nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04` | GPU 基础镜像 |
| `FACEID_GPU_DEVICES` | `all` | GPU 可见设备：`all`、`0`、`0,1` 等 |
| `UNIFACE_CACHE_DIR` | `/opt/uniface/models` | UniFace 模型缓存目录 |
| `UNIFACE_GITHUB_PROXY` | `https://gh-proxy.org/` | GitHub Release 下载代理 |
| `UNIFACE_MODEL_URL_REWRITE` | 空 | 模型 URL 前缀重写规则 |

## 模型下载和国内镜像

UniFace 模型默认来自 GitHub Releases。`hf-mirror.com` 只对 Hugging Face URL 有效，不能直接镜像这些 GitHub Release 地址。

默认使用：

```text
UNIFACE_GITHUB_PROXY=https://gh-proxy.org/
```

源地址：

```text
https://github.com/yakhyo/uniface/releases/download/weights/model.onnx
```

会被改写为：

```text
https://gh-proxy.org/https://github.com/yakhyo/uniface/releases/download/weights/model.onnx
```

如果你把模型同步到 ModelScope 或内部对象存储，可以配置 `UNIFACE_MODEL_URL_REWRITE`：

```text
UNIFACE_MODEL_URL_REWRITE=old_prefix=new_prefix,old_prefix_2=new_prefix_2
```

默认模型来源前缀：

```text
https://github.com/yakhyo/uniface/releases/download/weights/
https://github.com/yakhyo/face-anti-spoofing/releases/download/weights/
https://github.com/yakhyo/face-parsing/releases/download/weights/
```

`UNIFACE_MODEL_URL_REWRITE` 优先级高于 `UNIFACE_GITHUB_PROXY`。

### 构建阶段预下载

默认在 Docker build 阶段预下载模型：

```text
FACEID_PRELOAD_MODE=all
```

模式说明：

| 模式 | 下载内容 |
|------|----------|
| `all` | 检测、识别、反欺骗、人脸解析模型 |
| `core` | 检测、识别；默认开启活体时也包含反欺骗模型 |
| `none` | 构建阶段不下载模型 |

如果网络不稳定，可以设为 `none`，让运行时首次请求按需下载。构建阶段预下载更严格：模型下载失败会直接导致镜像构建失败，而不是第一次登录时失败。

## API

如果 `FACEID_API_KEY` 非空，所有 `/v1/*` 接口都需要：

```text
Authorization: Bearer <FACEID_API_KEY>
```

### 健康检查

```bash
curl http://127.0.0.1:8100/health
```

### 人脸比对

```bash
curl -X POST http://127.0.0.1:8100/v1/compare \
  -H "Content-Type: application/json" \
  -d '{
    "imageA": "data:image/jpeg;base64,...登录图片...",
    "imageB": "...已注册图片 base64..."
  }'
```

返回示例：

```json
{
  "matched": true,
  "score": 0.7812,
  "threshold": 0.6,
  "referenceIndex": 0,
  "probeIndex": 0,
  "reason": "matched",
  "liveness": {"isReal": true, "confidence": 0.91},
  "livenessThreshold": 0.7
}
```

批量比对：

```json
{
  "referenceImages": ["...已注册图片 1...", "...已注册图片 2..."],
  "probeImages": ["...登录图片 1...", "...登录图片 2..."]
}
```

请求级覆盖配置：

```json
{
  "imageA": "...",
  "imageB": "...",
  "enableLiveness": true,
  "similarityThreshold": 0.6,
  "livenessThreshold": 0.7
}
```

### 其他接口

```text
POST /v1/detect      {"image": "...base64..."}
POST /v1/anti-spoof  {"image": "...base64..."}
POST /v1/parse       {"image": "...base64..."}
```

## 常见问题

### GPU 显存一直是 0

如果日志里有：

```text
Failed to create CUDAExecutionProvider
libcublasLt.so.12: cannot open shared object file
```

说明容器里缺 CUDA 12/cuDNN 9 运行库。请使用默认 GPU 基础镜像：

```text
FACEID_GPU_BASE_IMAGE=nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04
```

### `/health` 显示已开启活体，但日志没看到活体检测

Uvicorn 默认只打印访问日志：

```text
POST /v1/compare HTTP/1.1" 200 OK
```

可以通过 `/health` 的 `livenessEnabled` 判断是否开启。活体失败时，`/v1/compare` 会返回 `reason: liveness_failed`。

### Casdoor 提示未录入人脸数据

检查用户是否存在 `faceIds[].imageUrl`，以及 Casdoor 后端容器是否能下载这个 URL。

### Local Storage 上传权限错误

检查 Local File System Storage Provider 的路径、容器 volume 和文件系统权限。保存到 `faceIds[].imageUrl` 的 URL 必须能被 Casdoor 后端访问。

## 安全建议

- 尽量只在内网暴露本服务。
- 本地开发外建议设置 `FACEID_API_KEY`。
- 不要在无认证、无网络隔离的情况下公开 `/v1/*` 接口。
- 人脸图片属于生物识别数据，需要保护 Casdoor 的存储、备份、日志和数据库访问权限。
- 活体检测可以降低简单照片攻击风险，但不能替代完整的风控体系。

## 许可证

本项目使用 [Apache License 2.0](./LICENSE)。

本项目依赖官方 [UniFace](https://github.com/yakhyo/uniface) 库。UniFace 使用 [MIT License](https://github.com/yakhyo/uniface/blob/main/LICENSE) 发布，本项目在使用 UniFace 时遵循其 MIT 许可证要求。第三方模型权重和其他上游组件可能有各自的许可证或使用条款，生产或商业使用前请单独确认。

## Star History

<div align="center">
  <a href="https://star-history.com/#dadastory/casdoor-faceid-service&Date">
    <img src="https://api.star-history.com/svg?repos=dadastory/casdoor-faceid-service&type=Date" alt="Star History Chart">
  </a>
</div>
