import uuid
from django.db import models
from django.db.models import Sum
from django.conf import settings
from decimal import Decimal
from django_countries.fields import CountryField
from products.models import Product
from profiles.models import UserProfile
from products.constants import ATTACHMENTS


class Order(models.Model):
    order_number = models.CharField(max_length=32, null=False, editable=False)
    user_profile = models.ForeignKey(UserProfile, on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='orders')
    full_name = models.CharField(max_length=50, null=False, blank=False)
    email = models.EmailField(max_length=254, null=False, blank=False)
    phone_number = models.CharField(max_length=20, null=False, blank=False)
    country = CountryField(blank_label='Country *', null=False, blank=False)
    postcode = models.CharField(max_length=20, null=True, blank=True)
    town_or_city = models.CharField(max_length=40, null=False, blank=False)
    street_address1 = models.CharField(max_length=80, null=False, blank=False)
    street_address2 = models.CharField(max_length=80, null=True, blank=True)
    county = models.CharField(max_length=80, null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True)
    delivery_cost = models.DecimalField(max_digits=6, decimal_places=2, null=False, default=0)
    order_total = models.DecimalField(max_digits=10, decimal_places=2, null=False, default=0)
    grand_total = models.DecimalField(max_digits=10, decimal_places=2, null=False, default=0)
    discount_applied = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, blank=True, null=True
    )
    original_bag = models.TextField(null=False, blank=False, default='')
    stripe_pid = models.CharField(max_length=254, null=False, blank=False, default='')
    loyalty_points = models.IntegerField(null=False, blank=False, default=0)
    loyalty_points_used = models.IntegerField(null=False, blank=False, default=0)

    def _generate_order_number(self):
        """
        Generate a random, unique order number using UUID
        """
        return uuid.uuid4().hex.upper()

    def loyalty_points_earned(self):
        """Calculate loyalty points based on the grand total."""
        return int(self.grand_total // 10)

    loyalty_points_earned.short_description = 'Loyalty Points Earned'

    def update_total(self, loyalty_points_used=0):
        """
        Update grand total each time a line item is added,
        accounting for delivery costs and adjusting for loyalty points used.
        """
        # Reset totals before recalculating
        self.order_total = self.lineitems.aggregate(Sum('lineitem_total'))['lineitem_total__sum'] or 0
        self.delivery_cost = 0

        # Recalculate delivery costs
        if self.order_total < settings.FREE_DELIVERY_THRESHOLD:
            self.delivery_cost = self.order_total * settings.STANDARD_DELIVERY_PERCENTAGE / 100

        # Calculate grand total before applying loyalty points
        self.grand_total = self.order_total + self.delivery_cost

        # Deduct loyalty points discount
        discount = Decimal(loyalty_points_used) * Decimal('0.1')  # $0.10 per point
        self.discount_applied = discount
        self.grand_total = max(self.grand_total - discount, Decimal('0.00'))

        # Update loyalty points earned
        self.loyalty_points = int(self.grand_total // 10)

        # Save applied loyalty points for future reference
        self.loyalty_points_used = loyalty_points_used
        self.save()

    def save(self, *args, **kwargs):
        """
        Override the original save method to set the order number
        if it hasn't been set already.
        """
        if not self.order_number:
            self.order_number = self._generate_order_number()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.order_number


class OrderLineItem(models.Model):
    order = models.ForeignKey(Order, null=False, blank=False, on_delete=models.CASCADE, related_name='lineitems')
    product = models.ForeignKey(Product, null=False, blank=False, on_delete=models.CASCADE)
    quantity = models.IntegerField(null=False, blank=False, default=0)
    attachments = models.TextField(null=True, blank=True)
    lineitem_total = models.DecimalField(max_digits=10, decimal_places=2, null=False, blank=False, editable=False)

    def get_attachment_price(self):
        """
        Calculate the total price of the attachments.
        The 'attachments' field contains a list of attachment SKUs.
        """
        total_attachment_price = Decimal(0)
        if self.attachments:
            attachment_skus = self.attachments.split(',')
            for attachment_sku in attachment_skus:
                for attachment in ATTACHMENTS:
                    if attachment['sku'] == attachment_sku:
                        total_attachment_price += Decimal(attachment['price'])
        return total_attachment_price

    def save(self, *args, **kwargs):
        """
        Override the original save method to set the lineitem total
        and update the order total.
        """
        self.lineitem_total = self.product.price * self.quantity

        attachment_total = self.get_attachment_price()
        self.lineitem_total += attachment_total * self.quantity

        super().save(*args, **kwargs)
        self.order.update_total(loyalty_points_used=self.order.loyalty_points_used)

    def get_readable_attachments(self):
        """
        Return a human-readable list of attachment names.
        """
        attachment_names = []
        if self.attachments:
            attachment_skus = self.attachments.split(',')
            for sku in attachment_skus:
                for attachment in ATTACHMENTS:
                    if attachment['sku'] == sku:
                        attachment_names.append(attachment['name'])
        return ', '.join(attachment_names)

    def __str__(self):
        return f'SKU {self.product.sku} on order {self.order.order_number}'
