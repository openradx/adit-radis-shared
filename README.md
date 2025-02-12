# ADIT-RADIS-Shared

## About

Shared Django apps between ADIT and RADIS.

## Example project

adit-radis-shared has an example app. To start it (for development):

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
