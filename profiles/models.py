from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django_countries.fields import CountryField
from products.models import Product


class LoyaltyPointsTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('EARN', 'Points Earned'),
        ('REDEEM', 'Points Redeemed'),
    ]

    user_profile = models.ForeignKey(
        'UserProfile',
        on_delete=models.CASCADE,
        related_name='points_transactions'
    )
    transaction_type = models.CharField(
        max_length=10,
        choices=TRANSACTION_TYPES
    )
    points = models.IntegerField()
    balance_before = models.IntegerField()
    balance_after = models.IntegerField()
    order = models.ForeignKey(
        'checkout.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.transaction_type} - {self.points} points"


class UserProfile(models.Model):
    """
    A user profile model for default delivery information and order history
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100, blank=True, null=True)
    default_phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )
    default_street_address1 = models.CharField(
        max_length=80,
        blank=True,
        null=True
    )
    default_street_address2 = models.CharField(
        max_length=80,
        blank=True,
        null=True
    )
    default_town_or_city = models.CharField(
        max_length=40,
        blank=True,
        null=True
    )
    default_county = models.CharField(max_length=80, blank=True, null=True)
    default_postcode = models.CharField(max_length=20, blank=True, null=True)
    default_country = CountryField(
        blank_label='Country',
        null=True,
        blank=True
    )
    loyalty_points = models.IntegerField(default=0, blank=True)

    def __str__(self):
        return self.user.username

    def adjust_loyalty_points(self, points_used, points_earned, order=None):
        """
        Adjust loyalty points without nested atomic transactions.
        """
        user_profile = UserProfile.objects.select_for_update().get(id=self.id)
        current_points = user_profile.loyalty_points

        points_deducted = 0
        points_added = 0

        try:
            # Redeem points first
            if points_used > 0:
                if current_points >= points_used:
                    # Create redemption transaction
                    self.points_transactions.create(
                        transaction_type='REDEEM',
                        points=-points_used,
                        balance_before=current_points,
                        balance_after=current_points - points_used,
                        order=order
                    )
                    current_points -= points_used
                    points_deducted = points_used
                else:
                    raise ValueError("Insufficient loyalty points to redeem")

            # Add earned points
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

            # Update the profile
            self.loyalty_points = current_points
            self.save()

            return points_deducted, points_added

        except Exception:
            raise


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

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='order_issues'
    )
    order = models.ForeignKey(
        'checkout.Order',
        on_delete=models.CASCADE,
        related_name='issues'
    )
    issue_type = models.CharField(max_length=20, choices=ISSUE_CHOICES)
    description = models.TextField()
    response = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='in_progress'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return (
            f"Issue - {self.issue_type} (Order: {self.order.order_number}) - "
            f"{self.get_status_display()}"
        )

    class Meta:
        permissions = [
            ("can_manage_issues", "Can manage customer issues"),
        ]


class Wishlist(models.Model):
    user_profile = models.OneToOneField(
        'UserProfile',
        on_delete=models.CASCADE,
        related_name='wishlist'
    )
    products = models.ManyToManyField(
        Product,
        related_name='wishlisted_by',
        blank=True
    )

    def __str__(self):
        return f"{self.user_profile.user.username}'s Wishlist"


@receiver(post_save, sender=UserProfile)
def create_user_wishlist(sender, instance, created, **kwargs):
    """
    Signal to create a wishlist for every new UserProfile.
    """
    if created:
        Wishlist.objects.create(user_profile=instance)


class RepairRequest(models.Model):
    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='repair_requests'
    )
    drone_model = models.CharField(max_length=255)
    issue_description = models.TextField()
    email = models.EmailField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='in_progress'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Repair - {self.drone_model} ({self.get_status_display()})"


class ContactMessage(models.Model):
    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='contact_messages'
    )
    name = models.CharField(max_length=255)
    email = models.EmailField()
    message = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='in_progress'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Contact - {self.name} ({self.get_status_display()})"


class UserMessage(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="messages"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sent_messages"
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    parent_message = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="responses"
    )
    repair_request = models.ForeignKey(
        'profiles.RepairRequest',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    contact_message = models.ForeignKey(
        'profiles.ContactMessage',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='messages'
    )

    def __str__(self):
        if self.repair_request:
            return (
                f"Message for Repair Request {self.repair_request.id} "
                f"from {self.created_by.username}"
            )
        elif self.contact_message:
            return (
                f"Message for Contact Message {self.contact_message.id} "
                f"from {self.created_by.username}"
            )
        return (
            f"Message from {self.created_by.username} "
            f"to {self.user.username}"
        )
