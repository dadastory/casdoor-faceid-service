ARG BASE_IMAGE=python:3.11-slim
FROM ${BASE_IMAGE}

ARG UNIFACE_EXTRA=cpu
ARG APT_MIRROR=http://mirrors.aliyun.com/debian
ARG APT_SECURITY_MIRROR=http://mirrors.aliyun.com/debian-security
ARG UBUNTU_MIRROR=http://mirrors.aliyun.com/ubuntu
ARG UBUNTU_SECURITY_MIRROR=http://mirrors.aliyun.com/ubuntu
ARG UV_DEFAULT_INDEX=https://mirrors.aliyun.com/pypi/simple/
ARG FACEID_PRELOAD_MODE=all
ARG UNIFACE_GITHUB_PROXY=https://gh-proxy.org/
ARG UNIFACE_MODEL_URL_REWRITE=

COPY --from=ghcr.io/astral-sh/uv:0.11.15 /uv /uvx /usr/local/bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_DEFAULT_INDEX=${UV_DEFAULT_INDEX} \
    UV_LINK_MODE=copy \
    FACEID_HOST=0.0.0.0 \
    FACEID_PORT=8100 \
    FACEID_PRELOAD_MODE=${FACEID_PRELOAD_MODE} \
    UNIFACE_GITHUB_PROXY=${UNIFACE_GITHUB_PROXY} \
    UNIFACE_MODEL_URL_REWRITE=${UNIFACE_MODEL_URL_REWRITE} \
    UNIFACE_CACHE_DIR=/opt/uniface/models \
    LD_LIBRARY_PATH="/usr/local/cuda/lib64:/usr/local/nvidia/lib:/usr/local/nvidia/lib64:${LD_LIBRARY_PATH}" \
    PATH="/app/.venv/bin:${PATH}"

WORKDIR /app

RUN set -eux; \
    if [ -f /etc/apt/sources.list ]; then \
      sed -i "s|http://deb.debian.org/debian|${APT_MIRROR}|g; s|http://security.debian.org/debian-security|${APT_SECURITY_MIRROR}|g; s|http://archive.ubuntu.com/ubuntu|${UBUNTU_MIRROR}|g; s|http://security.ubuntu.com/ubuntu|${UBUNTU_SECURITY_MIRROR}|g" /etc/apt/sources.list; \
    fi; \
    if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
      sed -i "s|http://deb.debian.org/debian|${APT_MIRROR}|g; s|http://security.debian.org/debian-security|${APT_SECURITY_MIRROR}|g" /etc/apt/sources.list.d/debian.sources; \
    fi; \
    if [ -f /etc/apt/sources.list.d/ubuntu.sources ]; then \
      sed -i "s|http://archive.ubuntu.com/ubuntu|${UBUNTU_MIRROR}|g; s|http://security.ubuntu.com/ubuntu|${UBUNTU_SECURITY_MIRROR}|g" /etc/apt/sources.list.d/ubuntu.sources; \
    fi; \
    apt-get update \
    && aptPackages="ca-certificates curl libgl1 libglib2.0-0" \
    && if ! command -v python >/dev/null 2>&1; then aptPackages="${aptPackages} python3 python3-pip python3-venv python-is-python3"; fi \
    && apt-get install -y --no-install-recommends ${aptPackages} \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock README.md ./
COPY casdoor_faceid_service ./casdoor_faceid_service

RUN uv sync --locked --no-dev --extra "${UNIFACE_EXTRA}" \
    && mkdir -p "${UNIFACE_CACHE_DIR}" \
    && uv run --no-sync python -m casdoor_faceid_service.preload

EXPOSE 8100

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8100/health', timeout=5)"

CMD ["python", "-m", "casdoor_faceid_service.main"]
