from django.contrib import admin
from .models import (
    OrderIssue, UserProfile, LoyaltyPointsTransaction, Wishlist,
    RepairRequest, ContactMessage, UserMessage
)


class UserMessageInline(admin.TabularInline):
    model = UserMessage
    extra = 0
    readonly_fields = (
        'user', 'created_by', 'content', 'created_at'
    )
    ordering = ('created_at',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if isinstance(self.parent_model, RepairRequest):
            return qs.filter(repair_request=self.parent_model)
        elif isinstance(self.parent_model, ContactMessage):
            return qs.filter(contact_message=self.parent_model)
        return qs


class LoyaltyPointsTransactionInline(admin.TabularInline):
    model = LoyaltyPointsTransaction
    extra = 0
    readonly_fields = (
        'user_profile', 'transaction_type', 'points',
        'balance_before', 'balance_after', 'created_at'
    )
    ordering = ('created_at',)


@admin.register(OrderIssue)
class OrderIssueAdmin(admin.ModelAdmin):
    list_display = ('order', 'user', 'issue_type', 'created_at', 'status')
    list_filter = ('issue_type', 'status', 'created_at')
    search_fields = ('order__order_number', 'user__username')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'loyalty_points')
    search_fields = ('user__username', 'full_name')


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user_profile',)
    search_fields = ('user_profile__user__username',)


@admin.register(RepairRequest)
class RepairRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'drone_model', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'drone_model')
    inlines = [UserMessageInline]


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'name', 'email')
    inlines = [UserMessageInline]


@admin.register(UserMessage)
class UserMessageAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'created_by', 'content', 'created_at',
        'repair_request', 'contact_message'
    )
    list_filter = ('created_at',)
    search_fields = (
        'user__username', 'created_by__username', 'content'
    )
