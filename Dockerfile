FROM python:3.12-slim

ARG UV_DEFAULT_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple
ARG UV_HTTP_TIMEOUT=180

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_DEFAULT_INDEX=${UV_DEFAULT_INDEX} \
    UV_HTTP_TIMEOUT=${UV_HTTP_TIMEOUT} \
    UV_CONCURRENT_DOWNLOADS=1 \
    PIP_INDEX_URL=${UV_DEFAULT_INDEX} \
    BILI_SUBTITLE_CONFIG_FILE=/config/service.yaml

WORKDIR /app

RUN python -m pip install --no-cache-dir uv

ENV PATH="/app/.venv/bin:${PATH}"

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
RUN uv sync --frozen --no-dev

RUN useradd --create-home --shell /usr/sbin/nologin bili-subtitle \
    && mkdir -p /config \
    && chown -R bili-subtitle:bili-subtitle /app /config

USER bili-subtitle

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD bili-subtitle-service healthcheck --port 8310

EXPOSE 8310 8311

CMD ["bili-subtitle-service", "serve", "--host", "0.0.0.0", "--port", "8310"]
