from typing import TypeGuard

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser

from adit_radis_shared.accounts.models import User


def is_logged_in_user(user: AbstractBaseUser | AnonymousUser) -> TypeGuard[User]:
    return user.is_authenticated
