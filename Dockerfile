# Ideas from https://docs.astral.sh/uv/guides/integration/docker/
# and https://hynek.me/articles/docker-uv/

FROM python:3.13-bookworm AS builder-base

ENV PYTHONUNBUFFERED=1 \
  PYTHONDONTWRITEBYTECODE=1 \
  UV_LINK_MODE=copy \
  UV_COMPILE_BYTECODE=1 \
  UV_PYTHON_DOWNLOADS=never \
  PATH="/app/.venv/bin:$PATH" \
  # There is no git during image build so we need to provide a fake version
  UV_DYNAMIC_VERSIONING_BYPASS=0.0.0

# Install dependencies for the `psql` command.
# Must match the version of the postgres service in the compose file!
RUN apt-get update \
  && apt-get install --no-install-recommends -y postgresql-common \
  && /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh -y \
  && apt-get install --no-install-recommends -y \
  postgresql-client-17 \
  && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.7.13 /uv /uvx /bin/

WORKDIR /app

###
# Development image
###
FROM builder-base AS development

# Install dependencies without project itself
RUN --mount=type=cache,target=/root/.cache/uv \
  --mount=type=bind,source=uv.lock,target=uv.lock \
  --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
  uv sync --frozen --no-install-project

RUN playwright install --with-deps chromium

ADD . /app

# Install project itself
RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --frozen

ARG PROJECT_VERSION
ENV PROJECT_VERSION=${PROJECT_VERSION}

###
# Production image
###
FROM builder-base AS production

# Install dependencies without dev and project itself
RUN --mount=type=cache,target=/root/.cache/uv \
  --mount=type=bind,source=uv.lock,target=uv.lock \
  --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
  uv sync --frozen --no-install-project --no-dev

ADD . /app

# Install project itself
RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --frozen --no-dev

ARG PROJECT_VERSION
ENV PROJECT_VERSION=${PROJECT_VERSION}
