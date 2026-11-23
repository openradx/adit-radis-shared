FROM mcr.microsoft.com/devcontainers/python:3.14-bookworm@sha256:6ed8a83ed447d20613b2a7160c710f70426c41f904da9a6c3a546c4c9f30f303

USER root

# Install system dependencies
# - gettext for Django translations
# - postgresql-common for the apt.postgresql.org.sh script
# - postgresql-client-17 for a current version of psql
# Make sure to match the version of the postgres service in the compose file!
RUN sudo apt-get update \
  && apt-get install -y --no-install-recommends \
  gettext \
  postgresql-common \
  && /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh -y \
  && apt-get install -y --no-install-recommends \
  postgresql-client-17 \
  && rm -rf /var/lib/apt/lists/*

USER vscode
