# Contributing to Our Project

We're excited that you're interested in contributing to our project! This document outlines the
guidelines for contributing to our codebase. We follow the Google Python Style Guide to maintain
consistency and readability across our project.

Code Style
We adhere to the Google Python Style [Guide](https://google.github.io/styleguide/pyguide.html).

## Introduction

ADIT-RADIS-Shared is the shared library for the ADIT and RADIS project. It contains the following
features:

- Password based authentication
- Token authentication for API access
- Common code small code utitilities

It also contains a Django example project to play around with the features.

## Getting Started

```terminal
git clone https://github.com/openradx/adit-radis-shared.git
cd adit-radis-shared
poetry install
poetry run ./cli.py compose-up
```

The development server of the example project will be started on <http://localhost:8000>

If a library dependency is changed, the containers need to be rebuilt (e.g. by running
`poetry run ./cli.py compose-down && poetry run ./cli.py compose-up`).
