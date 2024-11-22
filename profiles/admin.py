from django.contrib import admin
from .models import OrderIssue

@admin.register(OrderIssue)
class OrderIssueAdmin(admin.ModelAdmin):
    list_display = ('order', 'user', 'issue_type', 'created_at', 'status')
    list_filter = ('issue_type', 'status', 'created_at')
    search_fields = ('order__order_number', 'user__username')
