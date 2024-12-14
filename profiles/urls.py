from django.urls import path
from . import views

urlpatterns = [
    path('', views.profile, name='profile'),
    path('order_history/<order_number>', views.order_history, name='order_history'),
    path('report_issue/<order_number>/', views.report_order_issue, name='report_order_issue'),
    path('manage_issues/', views.manage_issues, name='manage_issues'),
    path('respond_to_issue/<int:issue_id>/', views.respond_to_issue, name='respond_to_issue'),
    path('messages/', views.messages_view, name='messages'),
    path("respond_to_message/<int:message_id>/", views.respond_to_message, name="respond_to_message"),
    path('manage-staff/', views.manage_staff, name='manage_staff'),
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/toggle/', views.toggle_wishlist, name='profiles_toggle_wishlist'),
    path('repairs/', views.handle_repair_submission, name='drone_repair'),
    path('contact/', views.handle_contact_submission, name='contact_us'),
    path('manage-messages/', views.manage_messages, name='manage_messages'),
    path('respond_to_repair_request/<int:request_id>/', views.respond_to_repair_request, name='respond_to_repair_request'),
    path('respond_to_contact_message/<int:message_id>/', views.respond_to_contact_message, name='respond_to_contact_message'),
]