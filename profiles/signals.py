from django.contrib.auth.models import Permission
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User


@receiver(post_save, sender=User)
def assign_manage_issues_permission(sender, instance, created, **kwargs):
    """
    Automatically assign or remove 'can_manage_issues' permission
    based on the staff status of the user.
    """
    try:
        # Fetch the 'can_manage_issues' permission
        permission = Permission.objects.get(codename='can_manage_issues')

        if instance.is_staff:
            # Add permission if the user is staff
            if not instance.has_perm('profiles.can_manage_issues'):
                instance.user_permissions.add(permission)
        else:
            # Remove permission if the user is not staff
            if instance.has_perm('profiles.can_manage_issues'):
                instance.user_permissions.remove(permission)

        # Save changes without re-triggering the signal
        if instance._state.adding or not instance.pk:
            return
    except Permission.DoesNotExist:
        # Log a warning if the permission does not exist
        print("Permission 'can_manage_issues' does not exist.")
