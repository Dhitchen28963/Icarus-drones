from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django_countries.fields import CountryField
from decimal import Decimal
from django.db import transaction


class LoyaltyPointsTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('EARN', 'Points Earned'),
        ('REDEEM', 'Points Redeemed'),
    ]

    user_profile = models.ForeignKey(
        'UserProfile', on_delete=models.CASCADE, related_name='points_transactions'
    )
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    points = models.IntegerField()
    balance_before = models.IntegerField()
    balance_after = models.IntegerField()
    order = models.ForeignKey(
        'checkout.Order', on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.transaction_type} - {self.points} points"


class UserProfile(models.Model):
    """
    A user profile model for maintaining default delivery information and order history
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100, blank=True, null=True)
    default_phone_number = models.CharField(max_length=20, blank=True, null=True)
    default_street_address1 = models.CharField(max_length=80, blank=True, null=True)
    default_street_address2 = models.CharField(max_length=80, blank=True, null=True)
    default_town_or_city = models.CharField(max_length=40, blank=True, null=True)
    default_county = models.CharField(max_length=80, blank=True, null=True)
    default_postcode = models.CharField(max_length=20, blank=True, null=True)
    default_country = CountryField(blank_label='Country', null=True, blank=True)
    loyalty_points = models.IntegerField(default=0, blank=True)

    def __str__(self):
        return self.user.username

    @transaction.atomic
    def adjust_loyalty_points(self, points_used, points_earned, order=None):
        """
        Adjust loyalty points with transaction logging in a single atomic transaction
        Returns tuple of (points_deducted, points_added) for confirmation
        """
        current_points = self.loyalty_points
        points_deducted = 0
        points_added = 0

        if points_used > 0 and current_points >= points_used:
            self.points_transactions.create(
                transaction_type='REDEEM',
                points=-points_used,
                balance_before=current_points,
                balance_after=current_points - points_used,
                order=order
            )
            current_points -= points_used
            points_deducted = points_used
            self.loyalty_points = current_points
            self.save()

        if points_earned > 0:
            self.points_transactions.create(
                transaction_type='EARN',
                points=points_earned,
                balance_before=current_points,
                balance_after=current_points + points_earned,
                order=order
            )
            current_points += points_earned
            points_added = points_earned
            self.loyalty_points = current_points
            self.save()

        return points_deducted, points_added


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    else:
        instance.userprofile.save()


class OrderIssue(models.Model):
    ISSUE_CHOICES = [
        ('not_received', 'Order Not Received'),
        ('damaged', 'Damaged Item(s)'),
        ('missing', 'Missing Item(s)'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='order_issues')
    order = models.ForeignKey(
        'checkout.Order', on_delete=models.CASCADE, related_name='issues'
    )
    issue_type = models.CharField(max_length=20, choices=ISSUE_CHOICES)
    description = models.TextField()
    response = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='in_progress'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Issue - {self.issue_type} (Order: {self.order.order_number}) - {self.get_status_display()}"

    class Meta:
        permissions = [
            ("can_manage_issues", "Can manage customer issues"),
        ]
