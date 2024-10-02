from django.contrib import admin
from .models import Order, OrderLineItem


class OrderLineItemAdminInline(admin.TabularInline):
    model = OrderLineItem
    readonly_fields = ('lineitem_total',)
    extra = 0  # Removes the extra empty inline rows


class OrderAdmin(admin.ModelAdmin):
    inlines = (OrderLineItemAdminInline,)

    readonly_fields = ('order_number', 'date',
                       'delivery_cost', 'order_total',
                       'grand_total', 'loyalty_points_earned',
                       'original_bag', 'stripe_pid')

    # Define the fields that will appear on the form when editing an order
    fields = ('order_number', 'user_profile', 'full_name',
              'email', 'phone_number', 'country',
              'postcode', 'town_or_city', 'street_address1',
              'street_address2', 'county', 'date',
              'delivery_cost', 'order_total', 'grand_total',
              'loyalty_points_earned', 'original_bag', 'stripe_pid')

    # List of columns to display in the admin panel order list view
    list_display = ('order_number', 'date', 'full_name',
                    'order_total', 'delivery_cost', 'grand_total',
                    'loyalty_points_earned')

    # Specify the default sorting for the order list view
    ordering = ('-date',)


# Register the Order model with the customized admin interface
admin.site.register(Order, OrderAdmin)
