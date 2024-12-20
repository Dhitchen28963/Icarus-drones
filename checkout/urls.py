from django.urls import path
from . import views
from checkout import webhooks

urlpatterns = [
    path('', views.checkout, name='checkout'),
    path(
        'checkout_success/<order_number>',
        views.checkout_success,
        name='checkout_success'
    ),
    path(
        'cache_checkout_data/',
        views.cache_checkout_data,
        name='cache_checkout_data'
    ),
    path('wh/', webhooks.webhook, name='webhook'),
    path(
        'update_payment_intent/',
        views.update_payment_intent,
        name='update_payment_intent'
    ),
]
