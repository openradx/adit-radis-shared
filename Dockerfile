FROM python:3.12-bullseye AS python-base

# python
# ENV variables are also available in the later build stages
ENV PYTHONUNBUFFERED=1 \
    # prevents python creating .pyc files
    PYTHONDONTWRITEBYTECODE=1 \
    \
    # pip
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    \
    # poetry
    # https://python-poetry.org/docs/#installing-with-the-official-installer
    # https://python-poetry.org/docs/configuration/#using-environment-variables
    POETRY_VERSION=1.8.3 \
    # make poetry install to this location
    POETRY_HOME="/opt/poetry" \
    # make poetry create the virtual environment in the project's root
    # it gets named `.venv`
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    # do not ask any interactive question
    POETRY_NO_INTERACTION=1 \
    \
    # paths
    # this is where our requirements + virtual environment will live
    PYSETUP_PATH="/opt/pysetup" \
    VENV_PATH="/opt/pysetup/.venv" \
    # needed for adit-radis-shared to be found
    PYTHONPATH="/app"

# prepend poetry and venv to path
ENV PATH="$POETRY_HOME/bin:$VENV_PATH/bin:$PATH"

# deps for db management commands
# make sure to match the postgres version to the service in the compose file
RUN apt-get update \
    && apt-get install --no-install-recommends -y postgresql-common \
    && /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh -y \
    && apt-get install --no-install-recommends -y \
    postgresql-client-17

# Install tzdata and configure timezone
ARG SYSTEM_TIME_ZONE
RUN apt-get install -y tzdata && \
    ln -fs /usr/share/zoneinfo/${SYSTEM_TIME_ZONE} /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata

# `builder-base` stage is used to build deps + create our virtual environment
FROM python-base AS builder-base
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
    # deps for installing poetry
    curl \
    # deps for building python deps
    build-essential

# install poetry - respects $POETRY_VERSION & $POETRY_HOME
RUN curl -sSL https://install.python-poetry.org | python3 -

# copy project requirement files here to ensure they will be cached.
WORKDIR $PYSETUP_PATH
COPY poetry.lock pyproject.toml ./

# install runtime deps - uses $POETRY_VIRTUALENVS_IN_PROJECT internally
RUN poetry install --without dev


# `development` image is used during development / testing
FROM python-base AS development
WORKDIR $PYSETUP_PATH

# copy in our built poetry + venv
COPY --from=builder-base $POETRY_HOME $POETRY_HOME
COPY --from=builder-base $PYSETUP_PATH $PYSETUP_PATH

# quicker install as runtime deps are already installed
RUN poetry install

# Install requirements for end-to-end testing
RUN playwright install --with-deps chromium

# will become mountpoint of our code
WORKDIR /app


# `production` image used for runtime
FROM python-base AS production
COPY --from=builder-base $PYSETUP_PATH $PYSETUP_PATH
COPY . /app/

WORKDIR /app
