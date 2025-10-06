#!/usr/bin/env bash

npm install
uv sync
uv run activate-global-python-argcomplete -y
uv run cli init-workspace
