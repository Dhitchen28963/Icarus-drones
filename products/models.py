from django.db import models


class Category(models.Model):

    class Meta:
        verbose_name_plural = 'Categories'

    name = models.CharField(max_length=254)
    friendly_name = models.CharField(max_length=254, null=True, blank=True)

    def __str__(self):
        return self.name

    def get_friendly_name(self):
        return self.friendly_name


class Product(models.Model):
    category = models.ForeignKey('Category', null=True, blank=True, on_delete=models.SET_NULL)
    sku = models.CharField(max_length=254, null=True, blank=True)
    name = models.CharField(max_length=254)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    rating = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    image = models.ImageField(null=True, blank=True)
    color = models.CharField(max_length=50, null=True, blank=True)
    rotors = models.IntegerField(null=True, blank=True)
    speed = models.CharField(max_length=50, null=True, blank=True)
    weight = models.CharField(max_length=50, null=True, blank=True)
    flight_time = models.CharField(max_length=50, null=True, blank=True)
    camera = models.CharField(max_length=10, null=True, blank=True)
    camera_quality = models.CharField(max_length=100, null=True, blank=True)
    collision_avoidance = models.CharField(max_length=10, null=True, blank=True)
    gps = models.CharField(max_length=10, null=True, blank=True)
    control_range = models.CharField(max_length=50, null=True, blank=True)
    max_altitude = models.CharField(max_length=50, null=True, blank=True)
    wind_resistance = models.CharField(max_length=50, null=True, blank=True)
    material = models.CharField(max_length=100, null=True, blank=True)
    remote_control = models.CharField(max_length=10, null=True, blank=True)
    mobile_app_support = models.CharField(max_length=50, null=True, blank=True)
    warranty = models.CharField(max_length=50, null=True, blank=True)
    compatibility = models.CharField(max_length=254, null=True, blank=True)
    package_contents = models.TextField(null=True, blank=True)
    drones_included = models.IntegerField(null=True, blank=True)
    drone_model = models.CharField(max_length=254, null=True, blank=True)
    accessories_included = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name
    
    
