from django.contrib import admin
from .models import Order, OrderLineItem


class OrderLineItemAdminInline(admin.TabularInline):
    model = OrderLineItem
    readonly_fields = ('lineitem_total', 'get_readable_attachments',)
    extra = 0
    fields = ('product', 'quantity', 'get_readable_attachments', 'lineitem_total')

    # Use human-readable names for attachments
    def get_readable_attachments(self, obj):
        return obj.get_readable_attachments()
    get_readable_attachments.short_description = 'Attachments'


class OrderAdmin(admin.ModelAdmin):
    inlines = (OrderLineItemAdminInline,)

    readonly_fields = ('order_number', 'date',
                       'delivery_cost', 'order_total',
                       'grand_total', 'loyalty_points_earned',
                       'original_bag', 'stripe_pid')

    fields = ('order_number', 'user_profile', 'date', 'full_name',
              'email', 'phone_number', 'country',
              'postcode', 'town_or_city', 'street_address1',
              'street_address2', 'county', 'delivery_cost', 
              'order_total', 'grand_total',
              'loyalty_points_earned', 'original_bag', 'stripe_pid')

    list_display = ('order_number', 'date', 'full_name',
                    'order_total', 'delivery_cost', 'grand_total',
                    'loyalty_points_earned')

    ordering = ('-date',)

admin.site.register(Order, OrderAdmin)
