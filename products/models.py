from django.db import models
from django.contrib.auth.models import User
import logging
from django.conf import settings
from custom_storages import MediaStorage

logger = logging.getLogger(__name__)


class Category(models.Model):
    class Meta:
        verbose_name_plural = 'Categories'

    name = models.CharField(max_length=254)
    friendly_name = models.CharField(
        max_length=254, null=True, blank=True
    )

    def __str__(self):
        return self.name

    def get_friendly_name(self):
        return self.friendly_name


class Product(models.Model):
    category = models.ForeignKey(
        'Category', null=True, blank=True,
        on_delete=models.SET_NULL
    )
    sku = models.CharField(
        max_length=254, null=True, blank=True
    )
    name = models.CharField(max_length=254)
    description = models.TextField()
    price = models.DecimalField(max_digits=7, decimal_places=2)
    rating = models.DecimalField(
        max_digits=6, decimal_places=2,
        null=True, blank=True
    )
    image = models.ImageField(
        null=True,
        blank=True,
        storage=MediaStorage(),
    )
    color = models.CharField(max_length=50, null=True, blank=True)
    rotors = models.IntegerField(null=True, blank=True)
    speed = models.CharField(max_length=50, null=True, blank=True)
    weight = models.CharField(max_length=50, null=True, blank=True)
    flight_time = models.CharField(max_length=50, null=True, blank=True)
    camera = models.CharField(
        max_length=3,
        choices=[("Yes", "Yes"), ("No", "No")],
        null=True, blank=True
    )
    camera_quality = models.CharField(
        max_length=100, null=True, blank=True
    )
    collision_avoidance = models.CharField(
        max_length=3,
        choices=[("Yes", "Yes"), ("No", "No")],
        null=True, blank=True
    )
    gps = models.CharField(
        max_length=3,
        choices=[("Yes", "Yes"), ("No", "No")],
        null=True, blank=True
    )
    control_range = models.CharField(
        max_length=50, null=True, blank=True
    )
    max_altitude = models.CharField(
        max_length=50, null=True, blank=True
    )
    wind_resistance = models.CharField(
        max_length=3,
        choices=[("Yes", "Yes"), ("No", "No")],
        null=True, blank=True
    )
    material = models.CharField(
        max_length=100, null=True, blank=True
    )
    remote_control = models.CharField(
        max_length=3,
        choices=[("Yes", "Yes"), ("No", "No")],
        null=True, blank=True
    )
    mobile_app_support = models.CharField(
        max_length=3,
        choices=[("Yes", "Yes"), ("No", "No")],
        null=True, blank=True
    )
    warranty = models.CharField(max_length=50, null=True, blank=True)
    compatibility = models.CharField(
        max_length=254, null=True, blank=True
    )
    package_contents = models.TextField(null=True, blank=True)
    drones_included = models.IntegerField(null=True, blank=True)
    drone_model = models.CharField(
        max_length=254, null=True, blank=True
    )
    accessories_included = models.TextField(null=True, blank=True)

    def save(self, *args, **kwargs):
        """Override save method to add logging"""
        logger.info(f"Saving product: {self.name}")

        if self.image:
            logger.info(f"Image details:")
            logger.info(f"  - Name: {self.image.name}")
            logger.info(f"  - Size: {getattr(self.image, 'size', 'N/A')}")

            # Enhanced storage logging
            storage = self.image.storage
            logger.info(f"Storage details:")
            logger.info(f"  - Class: {storage.__class__.__name__}")
            logger.info(f"  - Location: {getattr(storage, 'location', 'N/A')}")

            try:
                logger.info(f"  - URL: {self.image.url}")
            except Exception as e:
                logger.error(f"Error getting URL: {str(e)}")

        try:
            super().save(*args, **kwargs)
            logger.info(f"Successfully saved product {self.name}")

            if self.image:
                logger.info(f"Final image URL: {self.image.url}")
        except Exception as e:
            logger.error(f"Error saving product: {str(e)}")
            raise


class Attachment(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=7, decimal_places=2)
    sku = models.CharField(max_length=50, unique=True)
    image = models.ImageField(
        upload_to='attachments/', null=True, blank=True
    )

    def save(self, *args, **kwargs):
        """Override save method to add logging"""
        logger.info(f"Saving attachment: {self.name}")
        if self.image:
            logger.info(f"Attachment image: {self.image.name}")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ProductReview(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE,
        related_name='reviews'
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(
        choices=[(i, i) for i in range(1, 6)]
    )
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            f"{self.user.username} - "
            f"{self.product.name} ({self.rating} stars)"
        )

    def save(self, *args, **kwargs):
        """Override save method to add logging"""
        super().save(*args, **kwargs)
