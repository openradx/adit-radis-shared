# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ADIT-RADIS-Shared is a Django library providing reusable applications and utilities shared between the ADIT and RADIS medical imaging projects. It includes user authentication, token management, common utilities, and a CLI framework.

**License**: AGPL 3.0 or later

## Essential Commands

All commands use the `uv run cli` pattern:

```bash
# Development setup
uv sync                              # Install dependencies
cp ./example.env ./.env              # Create environment file
uv run cli compose-up -- --watch     # Start dev containers with hot reload
uv run cli compose-down              # Stop containers

# Code quality
uv run cli lint                      # Run ruff, pyright, djlint
uv run cli format-code               # Format with ruff and djlint

# Testing (requires containers running)
uv run cli test                      # Run all tests
uv run cli test -- -k test_name      # Run specific test
uv run cli test -- --cov             # Run with coverage

# Utilities
uv run cli shell                     # Python shell in web container
uv run cli copy-statics              # Copy npm packages to Django static folder
uv run cli show-outdated             # Check for outdated dependencies
uv run cli generate-auth-token       # Generate API authentication token
```

## Architecture

### Tech Stack

- **Backend**: Python 3.12+, Django 5.1.6+, PostgreSQL 17
- **Async**: Django Channels 4.2.0+, Daphne 4.1.2+ (ASGI server)
- **Task Queue**: Procrastinate 3.0.2+ (PostgreSQL-backed)
- **Frontend**: Bootstrap 5, HTMX 2.0.0, Alpine.js 3.14.0, Cotton components
- **API**: Django REST Framework 3.15.2+

### Django Apps (`adit_radis_shared/`)

- **accounts/**: Custom User model extending AbstractUser with `phone_number`, `department`, `preferences` (JSON), and `active_group` fields. Provides `ActiveGroupMiddleware` for group context switching in multi-organization setups.
- **token_authentication/**: REST API token auth with bcrypt-hashed storage (never plaintext). Tokens have `token_hashed`, `fraction` (4-char preview), `description`, `expires`, `last_used` fields. Uses `RestTokenAuthentication` class for DRF views.
- **common/**: Shared utilities including:
  - Models: `ProjectSettings`, `AppSettings` (abstract) for system configuration
  - Mixins: `LockedMixin`, `HtmxOnlyMixin`, `RelatedFilterMixin`, `PageSizeSelectMixin`, `RelatedPaginationMixin`
  - Types: `AuthenticatedHttpRequest`, `HtmxHttpRequest`, `AuthenticatedApiRequest`
  - `MaintenanceMiddleware` for site-wide maintenance mode with staff bypass
  - Template tags, mail utilities, async helpers, HTMX triggers
- **cli/**: Typer-based CLI commands for development, testing, and deployment

### Key Models

**User** (`accounts/models.py`):

- Extends `AbstractUser` with group-based access control
- `active_group`: Currently active group for users with multiple memberships
- `preferences`: JSON field for user-specific settings

**Token** (`token_authentication/models.py`):

- `token_hashed`: Bcrypt hash of the token (unique)
- `fraction`: First 4 characters for identification without exposing full token
- `expires`: Optional expiration datetime
- `last_used`: Tracks token usage for auditing

**ProjectSettings/AppSettings** (`common/models.py`):

- Singleton pattern for application configuration
- `announcement`: Site-wide announcement text
- `locked`: Maintenance mode flag

### Docker Services

- **web**: Django dev server with Daphne (port 8000)
- **worker**: Procrastinate background task processor
- **postgres**: PostgreSQL 17 database (port 5432)

### Key Patterns

- **INSTALLED_APPS order**: `daphne` first, then `adit_radis_shared.common` before `registration`
- **URL routing**: Include app URLs under `accounts/`, `token-authentication/`, `api/token-authentication/`
- **Frontend stack**: Bootstrap 5 + HTMX + Alpine.js (minimal JavaScript, no heavy frameworks)
- **Async support**: Django Channels with Daphne for WebSocket/async views

## Management Commands

```bash
# User management
./manage.py create_superuser          # Create admin user from env vars
./manage.py create_example_users      # Generate test users
./manage.py create_example_groups     # Generate test groups

# Background tasks
./manage.py bg_worker                 # Start Procrastinate worker

# Utilities
./manage.py copy_statics              # Sync JS libraries to static folder
```

## Environment Variables

Key variables in `.env` (see `example.env`):

- `ENVIRONMENT`: `development` or `production`
- `DJANGO_SECRET_KEY`: Cryptographic signing key
- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`: Database connection
- `POSTGRES_USER`, `POSTGRES_PASSWORD`: Database credentials
- `DJANGO_ALLOWED_HOSTS`: Comma-separated allowed hosts
- `DJANGO_CSRF_TRUSTED_ORIGINS`: Trusted origins for CSRF
- `ADMIN_USERNAME`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`: Initial superuser
- `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`: SMTP configuration

## Code Standards

- **Style Guide**: Google Python Style Guide
- **Line Length**: 100 characters (Ruff), 120 for templates (djlint)
- **Type Checking**: pyright in basic mode
- **Linting**: Ruff with E, F, I, DJ rules
- **Import Order**: isort with first-party: `["adit_radis_shared", "example_project"]`

## Key Dependencies

- **Django Channels**: WebSocket and async view support
- **Daphne**: ASGI server for Channels
- **Procrastinate**: PostgreSQL-backed async task queue
- **django-cotton**: Component-based templating
- **Crispy Forms + Bootstrap5**: Form styling
- **django-htmx**: HTMX integration helpers

## Testing

- **Framework**: pytest with pytest-django, pytest-asyncio, pytest-playwright
- **Settings**: `example_project.settings.test`
- **Test paths**: `adit_radis_shared/**/tests`, `example_project/**/tests`
- **Acceptance tests**: Require dev containers running, marked with `@pytest.mark.acceptance`
- **Timeout**: 60 seconds per test

### Test Fixtures (`pytest_fixtures.py`)

- `channels_live_server`: Live server fixture for async/WebSocket tests
- `in_memory_app`: In-memory Procrastinate connector for task queue testing
- `migrator_ext`: Extended migrator with Procrastinate table cleanup

## API Examples

### Token Authentication in DRF Views

```python
from rest_framework.views import APIView
from adit_radis_shared.token_authentication.authentication import RestTokenAuthentication

class MyAPIView(APIView):
    authentication_classes = [RestTokenAuthentication]

    def get(self, request):
        # request.user is authenticated via token
        return Response({"user": request.user.username})
```

### Creating Tokens Programmatically

```python
from adit_radis_shared.token_authentication.models import Token

# Create a token for a user
token, raw_token = Token.objects.create_token(
    user=user,
    description="API access for script",
    expires=None  # or datetime for expiration
)
# raw_token is only available at creation time - store it securely!
```

## Troubleshooting

### ActiveGroupMiddleware Errors

- Ensure user has at least one group assigned
- Check `active_group` is set when user has multiple groups
- Superusers bypass group checks

### Token Authentication Failures

- Tokens are hashed - you cannot retrieve the original token
- Check `expires` field for expired tokens
- Verify `last_used` is being updated (helps diagnose stale tokens)

### Procrastinate Tasks Not Running

- Ensure worker is started: `docker compose logs worker`
- Check PostgreSQL connectivity
- Verify task is registered with `@app.task` decorator

### HTMX Requests Not Working

- Use `HtmxHttpRequest` type hint for proper type checking
- Check `HX-Request` header is present
- Verify CSRF token is included in HTMX requests
