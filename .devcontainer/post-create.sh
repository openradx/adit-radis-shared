#!/usr/bin/env bash

npm install
uv sync
uv run cli --install-completion
uv run cli init-workspace
