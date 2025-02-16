#!/usr/bin/env bash

npm install
uv sync
uv run typer --install-completion
uv run ./cli.py init-workspace
