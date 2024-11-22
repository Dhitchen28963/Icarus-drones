from django.contrib.auth.models import Permission
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User

@receiver(post_save, sender=User)
def assign_manage_issues_permission(sender, instance, created, **kwargs):
    """
    Automatically assign 'can_manage_issues' permission to staff users.
    """
    if instance.is_staff:
        permission = Permission.objects.get(codename='can_manage_issues')
        if not instance.has_perm('profiles.can_manage_issues'):
            instance.user_permissions.add(permission)
            instance.save()
