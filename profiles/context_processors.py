def add_can_manage_issues(request):
    """
    Context processor to add `can_manage_issues` variable globally.
    """
    if not request.user.is_authenticated:
        return {}

    can_manage_issues = (
        request.user.is_superuser or
        request.user.has_perm('profiles.can_manage_issues')
    )

    return {
        'can_manage_issues': can_manage_issues,
    }
