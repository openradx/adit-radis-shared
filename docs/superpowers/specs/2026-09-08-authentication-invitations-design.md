# Replace django-registration-redux with django-allauth: invitation flow

**Date:** 2026-09-08
**Status:** Draft — distilled from the meeting decisions, pending review

Sources are tagged per requirement: **[M1]** concept meeting (August, Kai/Luca/Ritwik),
**[M2]** flow design meeting (early September), **[M3]** demo review meeting (2026-09-08).
Untagged statements are implementation decisions within the agreed frame.

## Background

Registration currently runs on django-registration-redux, which cannot speak OIDC and is
aging. The department wants an invitation-based sign up for username/password accounts,
replacing the old self-service registration with admin approval, and later a login through
an identity provider. This document covers the first pull request: the library switch and
the invitations. The identity provider login follows in a second, small pull request on top
(Kai, 2026-10-08). All of this is developed in the example project of adit-radis-shared
first; ADIT and RADIS adopt it later. [M1]

Authentication changes; authorization does not. Groups inside the app, the active group
mechanism and all permissions stay exactly as they are. [M1]

## Goal

One PR against adit-radis-shared that removes redux, lets allauth handle username/password
login, password change and password reset, and adds the invitation flow including the
admin's onboarding workflow. [M3]

## Non-goals

- The identity provider (OIDC) login. Second pull request, on top of this one. [M3]
- LDAP. Waits for the conversation with IT (Wolfgang) or a test LDAP server. [M1][M3]
- Migration of existing users. Explicitly last; nothing in this PR may assume it. [M2]
- Adoption in ADIT and RADIS. Separate PRs after this shape is approved. [M1]
- Pagination of the invitations table. Named as future work. [M3]
- Bulk invitations (list/CSV of addresses). Named as future work. [M3]
- Single sign-on across ADIT and RADIS. Open question, untouched here. [M1]

## Login

- L1. Username/password login, password change and password reset run through allauth.
  Redux and all its templates are removed. [M2]
- L2. The login page keeps the field labels "Username" and "Password" and the button
  "Log In", so the Playwright helper shared with ADIT and RADIS keeps working.
- L3. The backend order is our ActiveGroupModelBackend first, allauth's second; group
  and permission behaviour is identical for every kind of user. [M1]
- L4. Email addresses are unique across accounts. The old registration form enforced
  this at sign up; allauth keeps enforcing it.

## Invitations

### Creating

- I1. Only admins invite. Mechanically: the invitations page requires the
  accounts.add_invitation permission (superusers always pass). [M2][M3]
- I2. The page is reached from the admin section, not from the user menu. [M3]
- I3. The form is one email field and an Invite button. [M2]
- I4. An address that already has an account is refused. [M2][M3]
- I5. An address with a pending invitation is refused until that invitation is
  canceled or expires. [M3]
- I6. The invitee receives one mail with a tokenized link; the token is random
  (secrets.token_urlsafe), single use, and expires after INVITATION_VALID_DAYS
  (default 14). [M2]

### The list

- I7. Columns: email, invited by, sent, expires, status, actions.
- I8. Status is one of Pending, Expired, Signed up. "Signed up" means the sign-up form
  was completed — the signal that the admin's part can begin — and takes precedence
  over Expired. [M3]
- I9. A pending row offers Copy link (so an admin can hand the link over when mail
  delivery fails) and Cancel. Cancel deletes the invitation, invalidates the link and
  frees the address. Accepted invitations cannot be canceled. [M3]
- I10. A signed up row links directly to the created user in the Django admin. [M3]
- I11. Once the admin finished the onboarding (user active and in a group), the
  invitation disappears from the list. *Provisional — Kai wants to revisit whether a
  "finished" state should stay visible.* The row is only hidden, not deleted, so the
  decision stays reversible. [M3]

### Accepting and signing up

- I12. An unknown, expired or used token shows an "invalid invitation" page with
  HTTP status 410.
- I13. Opening a valid link logs out whoever is logged in, then leads to the sign-up
  page. Without a valid invitation in the session, sign up is closed.
- I14. The sign-up form shows the invitation's email locked; a submitted email is
  ignored. Username, first name, last name, phone number and department are required,
  as in the old registration form. [M2]
- I15. Submitting creates the user through allauth with the email marked verified
  (the link already proved ownership), links the user to the invitation and marks it
  accepted.
- I16. The created user is **deactivated**. They are not logged in; they see a waiting
  page. Activating the account and assigning a group is the admin's job, done on the
  user in the Django admin — reached through the link of I10. [M3]
- I17. The admins are mailed about the new user (ADMINS setting), with a direct link
  to that admin page. [M2]
- I18. The workflow assumes that whoever invites can also finish the onboarding:
  inviting needs only the add_invitation permission, while activating requires a
  staff account allowed to change users in the Django admin. Group setups in ADIT
  and RADIS must keep both capabilities on the same people.

## Notices

- N1. An authenticated user without an active group (an activated user not yet put into
  a group) sees a banner that an administrator has been informed and
  will assign them; superusers are excluded. [M2]

## Verification

- V1. Every numbered requirement is covered by at least one integration test under
  adit_radis_shared/accounts/tests/ (test_password_login,
  test_invitations). The tests are the executable form of this document.
- V2. Every test runs within the 60 second per-test timeout and needs no service
  beyond the database.
- V3. The Playwright acceptance tests of ADIT and RADIS log in through the shared
  helper — L2 exists so they stay untouched. The invitation flow itself is verified
  at the Django test client level only; see Q4.

## Open questions

- Q1. An accepted invitation whose user was deleted by the admin lingers as an
  actionless "Signed up" row. Probably: allow Cancel when the linked user is gone.
- Q2. The waiting page is also shown to deliberately deactivated users, for whom
  "an administrator has been informed" is not true. Wording could be neutralized.
- Q3. Whether finished invitations should reappear as a visible history (see I11).
- Q4. Whether a browser-level acceptance test must drive the invitation flow before
  ADIT and RADIS adopt it.
