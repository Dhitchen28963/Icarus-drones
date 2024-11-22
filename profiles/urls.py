from django.urls import path
from . import views

urlpatterns = [
    path('', views.profile, name='profile'),
    path('order_history/<order_number>', views.order_history, name='order_history'),
    path('report_issue/<order_number>/', views.report_order_issue, name='report_order_issue'),
    path('manage_issues/', views.manage_issues, name='manage_issues'),
    path('respond_to_issue/<int:issue_id>/', views.respond_to_issue, name='respond_to_issue'),
    path('messages/', views.messages_view, name='messages'),
    path('manage-staff/', views.manage_staff, name='manage_staff'),
]