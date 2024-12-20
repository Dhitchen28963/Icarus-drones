from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import user_passes_test


def superuser_or_staff_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if (
            request.user.is_superuser or
            request.user.has_perm('profiles.can_manage_issues')
        ):
            return view_func(request, *args, **kwargs)
        raise PermissionDenied
    return _wrapped_view


def superuser_required(view_func):
    return user_passes_test(lambda u: u.is_superuser)(view_func)
