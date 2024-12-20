from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from .models import Order, OrderLineItem
from products.models import Product
from profiles.models import UserProfile
from utils.mailchimp_utils import Mailchimp
import json
import stripe
import base64
import time
from decimal import Decimal
from django.db import transaction
from products.constants import ATTACHMENTS


class StripeWH_Handler:
    """Handle Stripe webhooks"""

    def __init__(self, request):
        self.request = request
        self.mailchimp = Mailchimp()

    def _send_confirmation_email(
        self, order, loyalty_points_earned, loyalty_points_used, discount
    ):
        try:
            # Helper to map SKUs to friendly names and prices
            def get_attachment_details(attachments_sku_list):
                attachment_details = []
                for sku in attachments_sku_list:
                    for attachment in ATTACHMENTS:
                        if attachment['sku'] == sku:
                            attachment_details.append(
                                f"{attachment['name']} "
                                f"(${attachment['price']})"
                            )
                return ", ".join(attachment_details)

            background_image_url = (
                "https://dhitchen28963-icarus-drones.s3.us-east-1."
                "amazonaws.com/media/homepage_background.webp"
            )
            facebook_icon_url = (
                "https://dhitchen28963-icarus-drones.s3.us-east-1."
                "amazonaws.com/media/facebook.png"
            )
            twitter_icon_url = (
                "https://dhitchen28963-icarus-drones.s3.us-east-1."
                "amazonaws.com/media/twitter.png"
            )
            instagram_icon_url = (
                "https://dhitchen28963-icarus-drones.s3.us-east-1."
                "amazonaws.com/media/instagram.png"
            )
            unsubscribe_url = (
                f"{settings.SITE_URL}/profiles/"
                f"unsubscribe/{order.email}/"
            )

            context = {
                'order': order,
                'contact_email': settings.DEFAULT_FROM_EMAIL,
                'loyalty_points_earned': loyalty_points_earned,
                'loyalty_points_used': loyalty_points_used,
                'discount_applied': f"${discount:.2f}",
                'background_image_url': background_image_url,
                'facebook_icon_url': facebook_icon_url,
                'twitter_icon_url': twitter_icon_url,
                'instagram_icon_url': instagram_icon_url,
                'unsubscribe_url': unsubscribe_url,
                'lineitems': [
                    {
                        'product_name': item.product.name,
                        'quantity': item.quantity,
                        'attachments': get_attachment_details(
                            item.attachments.split(',')
                        ) if item.attachments else '',
                        'lineitem_total': item.lineitem_total,
                    }
                    for item in order.lineitems.all()
                ],
            }

            subject = render_to_string(
                'checkout/confirmation_emails/confirmation_email_subject.txt',
                {'order': order},
            ).strip()
            text_content = render_to_string(
                'checkout/confirmation_emails/confirmation_email_body.txt',
                context,
            )
            html_content = render_to_string(
                'checkout/confirmation_emails/confirmation_email_body.html',
                context,
            )

            msg = EmailMultiAlternatives(
                subject,
                text_content,
                settings.DEFAULT_FROM_EMAIL,
                [order.email],
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send()
        except Exception as e:
            raise

    def handle_event(self, event):
        """Handle a generic/unknown/unexpected webhook event"""
        return HttpResponse(
            content=f'Unhandled event: {event["type"]}',
            status=200,
        )

    def _extract_loyalty_points(self, intent):
        try:
            return int(intent.metadata.get('loyalty_points_used', 0))
        except (ValueError, TypeError):
            return 0

    def handle_payment_intent_succeeded(self, event):
        try:
            intent = event.data.object
            pid = intent.id

            loyalty_points_used = self._extract_loyalty_points(intent)
            username = intent.metadata.get('username', 'AnonymousUser')
            bag = intent.metadata.get('bag', '{}')

            try:
                order = Order.objects.get(stripe_pid=pid)

                if (
                    order.user_profile
                    and order.loyalty_points_used > 0
                    and order.loyalty_points > 0
                ):
                    return HttpResponse(
                        content=(
                            f'Webhook received: {event["type"]} | '
                            "Order already processed"
                        ),
                        status=200,
                    )

                user_profile = order.user_profile
                if user_profile:
                    with transaction.atomic():
                        user_profile.adjust_loyalty_points(
                            points_used=order.loyalty_points_used,
                            points_earned=order.loyalty_points,
                            order=order,
                        )

                if not order.email:
                    order.email = intent.charges.data[0].billing_details.email
                    order.save()

                self._send_confirmation_email(
                    order,
                    order.loyalty_points,
                    order.loyalty_points_used,
                    order.discount_applied,
                )

                return HttpResponse(
                    content=(
                        f'Webhook received: {event["type"]} | '
                        "SUCCESS: Order processed"
                    ),
                    status=200,
                )

            except Order.DoesNotExist:
                for attempt in range(3):
                    time.sleep(1)
                    try:
                        order = Order.objects.get(stripe_pid=pid)

                        if (
                            order.user_profile
                            and order.loyalty_points_used > 0
                            and order.loyalty_points > 0
                        ):
                            return HttpResponse(
                                content=(
                                    f'Webhook received: {event["type"]} | '
                                    "Order already processed"
                                ),
                                status=200,
                            )

                        user_profile = order.user_profile
                        if user_profile:
                            with transaction.atomic():
                                user_profile.adjust_loyalty_points(
                                    points_used=order.loyalty_points_used,
                                    points_earned=order.loyalty_points,
                                    order=order,
                                )

                        if not order.email:
                            order.email = (
                                intent.charges.data[0].billing_details.email
                            )
                            order.save()

                        self._send_confirmation_email(
                            order,
                            order.loyalty_points,
                            order.loyalty_points_used,
                            order.discount_applied,
                        )

                        return HttpResponse(
                            content=(
                                f'Webhook received: {event["type"]} | '
                                "SUCCESS: Order processed"
                            ),
                            status=200,
                        )

                    except Order.DoesNotExist:
                        continue

                bag_items = json.loads(bag)
                order_total = Decimal('0.00')

                for item_data in bag_items.values():
                    product = Product.objects.get(sku=item_data['sku'])
                    quantity = item_data.get('quantity', 0)
                    item_price = product.price

                    if 'attachments' in item_data and item_data['attachments']:
                        for attachment_sku in item_data['attachments']:
                            for attachment in ATTACHMENTS:
                                if attachment['sku'] == attachment_sku:
                                    item_price += Decimal(
                                        str(attachment['price'])
                                    )

                    order_total += item_price * Decimal(str(quantity))

                delivery_cost = (
                    Decimal('10.00')
                    if order_total < Decimal('100.00')
                    else Decimal('0.00')
                )
                discount = Decimal(loyalty_points_used) * Decimal('0.1')
                grand_total = max(
                    order_total + delivery_cost - discount, Decimal('0.00')
                )
                loyalty_points_earned = int(grand_total // 10)

                charge = stripe.Charge.retrieve(intent.latest_charge)
                billing_details = charge.billing_details

                order, created = Order.objects.get_or_create(
                    stripe_pid=pid,
                    defaults={
                        'email': billing_details.email,
                        'full_name': billing_details.name,
                        'order_total': order_total,
                        'delivery_cost': delivery_cost,
                        'grand_total': grand_total,
                        'discount_applied': discount,
                        'loyalty_points_used': loyalty_points_used,
                        'loyalty_points': loyalty_points_earned,
                        'original_bag': bag,
                        'phone_number': billing_details.phone,
                        'country': billing_details.address.country,
                        'postcode': billing_details.address.postal_code,
                        'town_or_city': billing_details.address.city,
                        'street_address1': billing_details.address.line1,
                        'street_address2': billing_details.address.line2,
                        'county': billing_details.address.state,
                    }
                )

                if created:
                    for item_id, item_data in bag_items.items():
                        product = Product.objects.get(sku=item_data['sku'])
                        quantity = item_data.get('quantity', 0)
                        attachments = ','.join(
                            item_data.get('attachments', [])
                        )

                        order_line_item = OrderLineItem(
                            order=order,
                            product=product,
                            quantity=quantity,
                            attachments=attachments,
                        )
                        order_line_item.save()

                self._send_confirmation_email(
                    order, loyalty_points_earned, loyalty_points_used, discount
                )

                return HttpResponse(
                    content=(
                        f'Webhook received: {event["type"]} | SUCCESS'
                    ),
                    status=200,
                )

        except Exception as e:
            return HttpResponse(content=f'Error: {str(e)}', status=500)

    def handle_payment_intent_payment_failed(self, event):
        """Handle the payment_intent.payment_failed webhook from Stripe"""
        return HttpResponse(
            content=f'Webhook received: {event["type"]}',
            status=200,
        )
