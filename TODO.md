# TODO

## Shared

- Move shared invoke tasks to a common file (mayby adit-radis-shared/shared_tasks.py)
  - use them in ADIT and RADIS with e.g. `task(bump_version)`
- Get rid of pytz and reevaluate TimezoneMiddleware (is it really necessary?)
- Write an example to show pagination functionality
- Move populate_db into common app and rename to populate_users_and_groups
  - Reuse this command in the ADIT and RADIS

## ADIT / RADIS

- Add admin_section to main menu items
- Remove adit_radis_shared and instead install as package
- Remove sandbox
- Is Markdown package still needed?
- Get rid of subrepo stuff
- Reorder stuff in settings files
- Use django-environ as in the docs (see shared)
- Make package.json more minimal (as in shared)
- Get rid of static vendor stuff (its in common app now)
