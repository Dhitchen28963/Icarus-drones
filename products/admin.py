from django.contrib import admin
from .models import Category, Product, Attachment, ProductReview


class CategoryAdmin(admin.ModelAdmin):
    list_display = ('friendly_name', 'name')


class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'sku', 'name', 'category', 'price', 'rating', 'image', 'color'
    )
    ordering = ('sku',)
    list_filter = ('category', 'color', 'camera', 'gps')
    search_fields = ('name', 'sku', 'category__name')
    list_editable = ('price', 'rating', 'color')

    fieldsets = (
        (None, {
            'fields': (
                'sku', 'name', 'description', 'price', 'rating', 'image',
                'category'
            )
        }),
        ('Drone Fields', {
            'fields': (
                'color', 'rotors', 'speed', 'weight', 'flight_time',
                'camera', 'camera_quality', 'collision_avoidance', 'gps',
                'control_range', 'max_altitude', 'wind_resistance',
                'material', 'remote_control', 'mobile_app_support'
            ),
            'classes': ('collapse',),
        }),
        ('Accessory Fields', {
            'fields': ('compatibility', 'package_contents'),
            'classes': ('collapse',),
        }),
        ('Bundle Fields', {
            'fields': (
                'drones_included', 'drone_model', 'accessories_included',
                'warranty'
            ),
            'classes': ('collapse',),
        }),
    )


class AttachmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'price', 'sku', 'image')
    search_fields = ('name', 'sku')
    list_editable = ('price',)


class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'created_at')
    list_filter = ('product', 'rating', 'created_at')
    search_fields = ('product__name', 'user__username', 'comment')


admin.site.register(Category, CategoryAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(Attachment, AttachmentAdmin)
admin.site.register(ProductReview, ProductReviewAdmin)
