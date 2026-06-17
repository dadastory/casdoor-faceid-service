# Casdoor Face ID Service

Stateless Python service for Casdoor local Face ID login. It uses UniFace for face detection, recognition, optional anti-spoofing, and face parsing.

The service does not store user data, images, embeddings, or management records. Casdoor remains responsible for users, `faceIds`, uploaded resources, provider configuration, and deletion.

## Run

CPU:

```bash
docker compose --profile cpu up faceid-cpu
```

GPU:

```bash
docker compose --profile gpu up faceid-gpu
```

GPU defaults to all visible NVIDIA devices. To select specific devices:

```bash
FACEID_GPU_DEVICES=0 docker compose --profile gpu up faceid-gpu
FACEID_GPU_DEVICES=0,1 docker compose --profile gpu up faceid-gpu
FACEID_GPU_DEVICES=all docker compose --profile gpu up faceid-gpu
```

The service listens on `http://127.0.0.1:8100`.

The Docker image preloads the default UniFace models during build. This makes download failures fail the build instead of appearing on the first login request.

## Configuration

Environment variables:

```text
FACEID_DEVICE=cpu
FACEID_ENABLE_LIVENESS=false
FACEID_SIMILARITY_THRESHOLD=0.6
FACEID_LIVENESS_THRESHOLD=0.7
FACEID_DETECTOR=retinaface
FACEID_RECOGNIZER=arcface
FACEID_PARSER=bisenet
FACEID_MAX_IMAGE_BYTES=8388608
FACEID_PRELOAD_MODE=all
UNIFACE_CACHE_DIR=/opt/uniface/models
UNIFACE_MODEL_URL_REWRITE=
FACEID_GPU_DEVICES=all
```

`FACEID_DEVICE=gpu` selects `CUDAExecutionProvider` with CPU fallback. `FACEID_DEVICE=cpu` forces `CPUExecutionProvider`.

`FACEID_PRELOAD_MODE=all` downloads the default detector, recognizer, anti-spoofing, and parsing models at image build time. Set it to `core` to preload only the login compare models, or `none` to disable build-time model download.

## Model Mirrors

UniFace currently publishes the default model weights through GitHub Releases. `hf-mirror.com` only helps for Hugging Face URLs, so it will not mirror these GitHub Release URLs directly.

Use `UNIFACE_MODEL_URL_REWRITE` to rewrite model URL prefixes during Docker build and runtime fallback downloads:

```text
UNIFACE_MODEL_URL_REWRITE=old_prefix=new_prefix,old_prefix_2=new_prefix_2
```

Generic GitHub proxy example:

```yaml
args:
  UNIFACE_MODEL_URL_REWRITE: "https://github.com/=https://gh-proxy.example.com/https://github.com/"
environment:
  UNIFACE_MODEL_URL_REWRITE: "https://github.com/=https://gh-proxy.example.com/https://github.com/"
```

If you sync the weights to ModelScope or an internal object store, map each source release prefix to the mirrored prefix. The default `all` preload uses these upstream prefixes:

```text
https://github.com/yakhyo/uniface/releases/download/weights/
https://github.com/yakhyo/face-anti-spoofing/releases/download/weights/
https://github.com/yakhyo/face-parsing/releases/download/weights/
```

Example after mirroring the same filenames:

```yaml
args:
  UNIFACE_MODEL_URL_REWRITE: "https://github.com/yakhyo/uniface/releases/download/weights/=https://modelscope.example.com/uniface/,https://github.com/yakhyo/face-anti-spoofing/releases/download/weights/=https://modelscope.example.com/face-anti-spoofing/,https://github.com/yakhyo/face-parsing/releases/download/weights/=https://modelscope.example.com/face-parsing/"
environment:
  UNIFACE_MODEL_URL_REWRITE: "https://github.com/yakhyo/uniface/releases/download/weights/=https://modelscope.example.com/uniface/,https://github.com/yakhyo/face-anti-spoofing/releases/download/weights/=https://modelscope.example.com/face-anti-spoofing/,https://github.com/yakhyo/face-parsing/releases/download/weights/=https://modelscope.example.com/face-parsing/"
```

## API

Health:

```bash
curl http://127.0.0.1:8100/health
```

Casdoor provider compare endpoint:

```bash
curl -X POST http://127.0.0.1:8100/v1/compare \
  -H "Content-Type: application/json" \
  -d '{
    "imageA": "data:image/png;base64,...login image...",
    "imageB": "...registered image base64...",
    "enableLiveness": true
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

Batch compare is also supported:

```json
{
  "referenceImages": ["...registered image 1...", "...registered image 2..."],
  "probeImages": ["...login image 1...", "...login image 2..."]
}
```

Additional endpoints:

```text
POST /v1/detect      {"image": "...base64..."}
POST /v1/anti-spoof  {"image": "...base64..."}
POST /v1/parse       {"image": "...base64..."}
```

## Casdoor Integration Shape

Add a Casdoor Face ID provider type such as `Local UniFace` and configure its endpoint as:

```text
http://faceid-cpu:8100
```

The Go provider only needs to call `POST /v1/compare` from its existing `Check(base64ImageA, base64ImageB)` path. Casdoor can pass per-provider liveness and threshold settings as request fields.
