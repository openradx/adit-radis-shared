# ADIT-RADIS-Shared

## About

Shared Django apps between ADIT and RADIS.

## Example project

adit-radis-shared has an example app. To start it (for development):

## Invitations

New users with a username and password can only sign up with an invitation. Users with the
`accounts.add_invitation` permission open the invitations page from the admin section, where they
enter an email address. The invitee gets a mail with a link to the sign-up page that is valid
for `INVITATION_VALID_DAYS`. After the sign up the admins get a mail, as only they can put the new user into a group.

## Available apps

### adit_radis_shared.common

Contains common stuff as well as the vendor statics and overwritten templates of django-allauth.
Therefore it must be added before `allauth` in `INSTALLED_APPS`.

### adit_radis_shared.accounts

Contains the custom user model and user profile stuff.

### adit_radis_shared.token_authentication

Token authentication support to access the API of ADIT and RADIS by using a REST API.

## License

- AGPL 3.0 or later
