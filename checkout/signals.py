from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import OrderLineItem


@receiver(post_save, sender=OrderLineItem)
def update_on_save(sender, instance, created, **kwargs):
    """
    Update order total on lineitem update/create include loyalty points used.
    """
    loyalty_points_used = instance.order.loyalty_points_used or 0
    instance.order.update_total(loyalty_points_used=loyalty_points_used)


@receiver(post_delete, sender=OrderLineItem)
def update_on_delete(sender, instance, **kwargs):
    """
    Update order total on lineitem delete, accounting for loyalty points used.
    """
    loyalty_points_used = instance.order.loyalty_points_used or 0
    instance.order.update_total(loyalty_points_used=loyalty_points_used)
