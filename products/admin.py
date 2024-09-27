from django.contrib import admin
from .models import Category, Product

# Admin for Category
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('friendly_name', 'name')

# Admin for Product
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'sku', 'name', 'category', 'price', 'rating', 
        'image', 'color', 'rotors', 'speed', 'weight',
        'flight_time', 'camera', 'camera_quality', 'collision_avoidance', 
        'gps', 'control_range', 'max_altitude', 'wind_resistance', 
        'material', 'remote_control', 'mobile_app_support', 
        'warranty', 'compatibility', 'package_contents', 
        'drones_included', 'drone_model', 'accessories_included'
    )
    ordering = ('sku',)
    list_filter = ('category', 'color', 'camera', 'gps')
    search_fields = ('name', 'sku', 'category__name')
    list_editable = ('price', 'rating', 'color')

admin.site.register(Category, CategoryAdmin)
admin.site.register(Product, ProductAdmin)
