from django.contrib.auth.decorators import login_required
from profiles.models import UserProfile

def add_can_manage_issues(request):
    """
    Context processor to add `can_manage_issues` variable globally for templates.
    """
    if not request.user.is_authenticated:
        return {}

    can_manage_issues = (
        request.user.is_superuser or request.user.has_perm('profiles.can_manage_issues')
    )

    return {
        'can_manage_issues': can_manage_issues,
    }
