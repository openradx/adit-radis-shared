#!/usr/bin/env bash

npm install
uv sync
uv run activate-global-python-argcomplete
uv run ./cli.py init_workspace
