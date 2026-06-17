# Casdoor Face ID Service

<div align="center">
  <h3>Local UniFace-backed Face ID service for Casdoor</h3>

  <p>
    <strong>A stateless Python face analysis service for local Casdoor Face ID login.</strong><br>
    Face detection, recognition, liveness detection, and face parsing are powered by
    <a href="https://github.com/yakhyo/uniface">UniFace</a>.
  </p>

  <p>
    <a href="README.zh-CN.md"><strong>中文说明</strong></a>
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

## Table of Contents

- [What It Does](#what-it-does)
- [How It Works](#how-it-works)
- [Features](#features)
- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [Casdoor Integration](#casdoor-integration)
- [User Enrollment](#user-enrollment)
- [Configuration](#configuration)
- [Model Downloads and Mirrors](#model-downloads-and-mirrors)
- [API](#api)
- [Troubleshooting](#troubleshooting)
- [Security](#security)
- [License](#license)
- [Star History](#star-history)

## What It Does

Casdoor Face ID Service is a local face recognition companion service for Casdoor. It is designed for a Casdoor fork that adds a `Local UniFace` Face ID provider, so Casdoor can provide Face ID login without using Alibaba Cloud Facebody.

The service is intentionally stateless:

- It does not store users.
- It does not store registered face images.
- It does not store embeddings or management records.
- Casdoor remains responsible for users, `faceIds`, uploaded resources, providers, and deletion.

## How It Works

The login flow is:

```text
Browser
  | 1. Captures the login face image
  v
Casdoor
  | 2. Reads user.faceIds[].imageUrl from the Casdoor user profile
  | 3. Downloads the registered face image through Casdoor Storage
  | 4. Sends both images to POST /v1/compare
  v
casdoor-faceid-service
  | 5. Optionally checks liveness on the login image
  | 6. Detects one face in each image
  | 7. Extracts normalized face embeddings
  | 8. Compares embeddings and returns matched=true/false
  v
Casdoor login result
```

Only the login probe image is checked for liveness. Registered images are enrollment data managed by Casdoor.

Internally, the service uses the official [UniFace](https://github.com/yakhyo/uniface) Python library:

- Detection: `RetinaFace` by default.
- Recognition: `ArcFace` by default.
- Anti-spoofing: `MiniFASNet` when liveness is enabled.
- Parsing: `BiSeNet` by default.
- Runtime backend: ONNX Runtime CPU or CUDA providers.

## Features

| Area | Support |
|------|---------|
| Face detection | RetinaFace by default; SCRFD, YOLOv5Face, YOLOv8Face are selectable |
| Face recognition | ArcFace by default; AdaFace, EdgeFace, MobileFace, SphereFace are selectable |
| Liveness detection | Enabled by default with MiniFASNet anti-spoofing |
| Face parsing | BiSeNet by default; XSeg is selectable |
| Runtime | Separate CPU and GPU Docker Compose profiles |
| GPU | ONNX Runtime CUDA provider with CPU fallback |
| Security | Optional Bearer token authentication for `/v1/*` APIs |
| Deployment | Docker, Docker Compose, uv-managed dependencies, China-friendly mirrors |

## Requirements

CPU deployment:

- Docker with Docker Compose v2.

GPU deployment:

- NVIDIA driver on the host.
- NVIDIA Container Toolkit.
- A CUDA 12 + cuDNN 9 runtime image. The default is `nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04`.

## Quick Start

Create local configuration:

```bash
cp .env.example .env
```

Run with CPU:

```bash
docker compose --profile cpu up -d --build faceid-cpu
```

Run with GPU:

```bash
docker compose --profile gpu up -d --build faceid-gpu
```

Check health:

```bash
curl http://127.0.0.1:8100/health
```

Expected response:

```json
{
  "status": "ok",
  "service": "casdoor-faceid-service",
  "device": "cpu",
  "livenessEnabled": true
}
```

### GPU Selection

Use all visible GPUs:

```bash
FACEID_GPU_DEVICES=all docker compose --profile gpu up -d faceid-gpu --build
```

Use one GPU:

```bash
FACEID_GPU_DEVICES=0 docker compose --profile gpu up -d faceid-gpu --build
```

Use multiple GPUs:

```bash
FACEID_GPU_DEVICES=0,1 docker compose --profile gpu up -d faceid-gpu --build
```

The service still starts one process. Multiple visible GPUs mainly control which devices ONNX Runtime may use.

## Casdoor Integration

This service requires a Casdoor fork that contains the `Local UniFace` Face ID provider.

Create or edit a Casdoor provider:

```text
Category: Face ID
Type: Local UniFace
Endpoint: http://172.17.0.1:8100
Client secret: <same value as FACEID_API_KEY, or empty for local development>
```

If Casdoor and this service are in the same Docker Compose network, a service name can be used:

```text
Endpoint: http://faceid-cpu:8100
```

If Casdoor runs in Docker and this service publishes port `8100` on the host, use an address reachable from the Casdoor container:

```text
Endpoint: http://172.17.0.1:8100
```

`Local UniFace` does not need Alibaba Cloud keys. It only needs `Endpoint` and optional `Client secret`.

## User Enrollment

Casdoor stores registered face data on the user object:

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

The image is uploaded through Casdoor Resource/Storage first, then the returned URL is written into `faceIds[].imageUrl`.

Self-service enrollment flow:

1. The user first signs in with password, verification code, OAuth, or another non-Face-ID method.
2. The user opens Casdoor `/account`.
3. The organization account item `Face ID` must be visible and modifiable by `Self`.
4. The user uploads a face image or captures one with the camera.
5. The user can use Face ID on later logins.

For business applications, add a link such as:

```text
https://<casdoor-host>/account
```

to your own "Account settings" or "Bind Face ID" page.

### Local Storage Notes

For Local File System storage, Casdoor generates file URLs from the storage provider `Domain`:

```text
<Domain>/files/<objectKey>
```

Casdoor backend must be able to access the stored `imageUrl`. If Casdoor runs in Docker, avoid storing URLs such as `http://127.0.0.1:8000/files/...` unless that address is reachable from inside the Casdoor container.

For a local Docker deployment, a common storage domain is:

```text
http://172.17.0.1:18000
```

If the storage domain changes later, existing `faceIds[].imageUrl` values may point to old URLs. Keep a stable domain or update user data.

## Configuration

Copy `.env.example` to `.env` and adjust values.

| Variable | Default | Description |
|----------|---------|-------------|
| `FACEID_PORT` | `8100` | Host port published by Docker Compose |
| `FACEID_API_KEY` | empty | Optional Bearer token for `/v1/*` APIs |
| `FACEID_ENABLE_LIVENESS` | `true` | Enable anti-spoofing during compare |
| `FACEID_SIMILARITY_THRESHOLD` | `0.6` | Minimum similarity score for a match |
| `FACEID_LIVENESS_THRESHOLD` | `0.7` | Minimum liveness confidence |
| `FACEID_DETECTOR` | `retinaface` | `retinaface`, `scrfd`, `yolov5`, or `yolov8` |
| `FACEID_RECOGNIZER` | `arcface` | `arcface`, `adaface`, `edgeface`, `mobileface`, or `sphereface` |
| `FACEID_PARSER` | `bisenet` | `bisenet` or `xseg` |
| `FACEID_MAX_IMAGE_BYTES` | `8388608` | Maximum decoded upload size |
| `FACEID_PRELOAD_MODE` | `all` | `all`, `core`, or `none` |
| `FACEID_CPU_BASE_IMAGE` | `python:3.11-slim` | CPU Docker base image |
| `FACEID_GPU_BASE_IMAGE` | `nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04` | GPU Docker base image |
| `FACEID_GPU_DEVICES` | `all` | GPU visibility: `all`, `0`, `0,1`, etc. |
| `UNIFACE_CACHE_DIR` | `/opt/uniface/models` | UniFace model cache directory |
| `UNIFACE_GITHUB_PROXY` | `https://gh-proxy.org/` | GitHub Release download proxy |
| `UNIFACE_MODEL_URL_REWRITE` | empty | Explicit model URL prefix rewrite rules |

## Model Downloads and Mirrors

UniFace model weights are downloaded from GitHub Releases. `hf-mirror.com` only mirrors Hugging Face URLs, so it does not help for these GitHub Release URLs directly.

By default, this project uses:

```text
UNIFACE_GITHUB_PROXY=https://gh-proxy.org/
```

A source URL like:

```text
https://github.com/yakhyo/uniface/releases/download/weights/model.onnx
```

is rewritten to:

```text
https://gh-proxy.org/https://github.com/yakhyo/uniface/releases/download/weights/model.onnx
```

To use your own mirror or ModelScope/object-store mirror, set `UNIFACE_MODEL_URL_REWRITE`:

```text
UNIFACE_MODEL_URL_REWRITE=old_prefix=new_prefix,old_prefix_2=new_prefix_2
```

Common upstream prefixes:

```text
https://github.com/yakhyo/uniface/releases/download/weights/
https://github.com/yakhyo/face-anti-spoofing/releases/download/weights/
https://github.com/yakhyo/face-parsing/releases/download/weights/
```

`UNIFACE_MODEL_URL_REWRITE` takes precedence over `UNIFACE_GITHUB_PROXY`.

### Build-Time Preload

The Docker image preloads UniFace models at build time by default:

```text
FACEID_PRELOAD_MODE=all
```

Modes:

| Mode | Models |
|------|--------|
| `all` | detector, recognizer, anti-spoofing, parser |
| `core` | detector, recognizer, and anti-spoofing when liveness is enabled |
| `none` | no build-time model download |

Use `none` if your network is unstable and you prefer runtime lazy downloads. Build-time preload is stricter: model download failures fail the image build instead of failing the first login request.

## API

All `/v1/*` APIs require:

```text
Authorization: Bearer <FACEID_API_KEY>
```

when `FACEID_API_KEY` is not empty.

### Health

```bash
curl http://127.0.0.1:8100/health
```

### Compare

```bash
curl -X POST http://127.0.0.1:8100/v1/compare \
  -H "Content-Type: application/json" \
  -d '{
    "imageA": "data:image/jpeg;base64,...login image...",
    "imageB": "...registered image base64..."
  }'
```

Response:

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

Batch compare:

```json
{
  "referenceImages": ["...registered image 1...", "...registered image 2..."],
  "probeImages": ["...login image 1...", "...login image 2..."]
}
```

Request-level overrides:

```json
{
  "imageA": "...",
  "imageB": "...",
  "enableLiveness": true,
  "similarityThreshold": 0.6,
  "livenessThreshold": 0.7
}
```

### Additional Endpoints

```text
POST /v1/detect      {"image": "...base64..."}
POST /v1/anti-spoof  {"image": "...base64..."}
POST /v1/parse       {"image": "...base64..."}
```

## Troubleshooting

### GPU memory stays at 0

If logs contain:

```text
Failed to create CUDAExecutionProvider
libcublasLt.so.12: cannot open shared object file
```

the container does not include CUDA 12/cuDNN 9 runtime libraries. Rebuild with:

```text
FACEID_GPU_BASE_IMAGE=nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04
```

### `/health` says liveness is enabled but logs do not show it

The default Uvicorn logs only show access lines such as:

```text
POST /v1/compare HTTP/1.1" 200 OK
```

Use `/health` to confirm `livenessEnabled`. A liveness failure returns `reason: liveness_failed` from `/v1/compare`.

### Casdoor says no face data was enrolled

Check that the user has at least one `faceIds[].imageUrl`, and that the Casdoor backend container can download that URL.

### Local storage upload has permission errors

Check the Local File System storage provider path, container volume, and filesystem owner. The URL stored in `faceIds[].imageUrl` must be reachable by Casdoor backend.

## Security

- Put this service on an internal network whenever possible.
- Set `FACEID_API_KEY` outside local development.
- Do not expose `/v1/*` publicly without authentication and network controls.
- Face images are biometric data. Protect Casdoor storage, backups, logs, and database access accordingly.
- Liveness detection reduces simple spoofing risk, but it is not a complete fraud-prevention system by itself.

## License

This project is licensed under the [Apache License 2.0](./LICENSE).

This project depends on the official [UniFace](https://github.com/yakhyo/uniface) library. UniFace is distributed under the [MIT License](https://github.com/yakhyo/uniface/blob/main/LICENSE), and this project is designed to use UniFace in compliance with that license. Third-party model weights and additional upstream components may have their own licenses or usage terms. Review them before production or commercial use.

## Star History

<div align="center">
  <a href="https://star-history.com/#dadastory/casdoor-faceid-service&Date">
    <img src="https://api.star-history.com/svg?repos=dadastory/casdoor-faceid-service&type=Date" alt="Star History Chart">
  </a>
</div>
