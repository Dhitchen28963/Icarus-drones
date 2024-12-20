from django.shortcuts import render


def index(request):
    can_manage_issues = (
        request.user.is_authenticated
        and (
            request.user.is_superuser or
            request.user.has_perm('profiles.can_manage_issues')
        )
    )

    return render(request, 'home/index.html', {
        'can_manage_issues': can_manage_issues,
    })
