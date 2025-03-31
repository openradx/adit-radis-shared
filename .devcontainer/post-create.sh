#!/usr/bin/env bash

npm install
uv sync
uv run activate-global-python-argcomplete
uv run ./scripts/init-workspace.py
