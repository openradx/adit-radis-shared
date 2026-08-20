# ADIT-RADIS-Shared

## About

Shared Django apps between ADIT and RADIS.

## Example project

adit-radis-shared has an example app. To start it (for development):

## OIDC login during development

The dev compose file contains a Keycloak service that serves as identity provider. It imports
the realm in the `keycloak` folder on startup, including a client and a user (`kc-user` /
`kc-user`). The Keycloak admin interface is served under <http://keycloak.local:8090>.

In production the identity provider is a separate service that is not part of this stack, so
Keycloak is only started when its compose profile is enabled:

```
COMPOSE_PROFILES=keycloak uv run cli compose-up
```

The browser and the containers must reach Keycloak under the same URL, otherwise the issuer in
the discovery document does not match. Therefore add the following line to the `/etc/hosts` file
of the host:

```
127.0.0.1 keycloak.local
```

The OIDC login is only offered when `OIDC_SERVER_URL` is set in the `.env` file.

## Available apps

### adit_radis_shared.common

Contains common stuff as well as the vendor statics and overwritten templates of the registration app.
Therefore it must be added directly before `registration` in `INSTALLED_APPS`.

### adit_radis_shared.accounts

Contains the custom user model and user profile stuff.

### adit_radis_shared.token_authentication

Token authentication support to access the API of ADIT and RADIS by using a REST API.

## License

- AGPL 3.0 or later
