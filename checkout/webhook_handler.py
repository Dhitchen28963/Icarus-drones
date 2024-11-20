from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import Order, OrderLineItem
from products.models import Product
from profiles.models import UserProfile
import json
import stripe
from decimal import Decimal


class StripeWH_Handler:
    """Handle Stripe webhooks"""

    def __init__(self, request):
        self.request = request

    def _send_confirmation_email(self, order, loyalty_points_earned, loyalty_points_used, discount):
        """Send the user a confirmation email"""
        cust_email = order.email
        subject = render_to_string(
            'checkout/confirmation_emails/confirmation_email_subject.txt',
            {'order': order}
        ).strip()
        body = render_to_string(
            'checkout/confirmation_emails/confirmation_email_body.txt',
            {
                'order': order,
                'contact_email': settings.DEFAULT_FROM_EMAIL,
                'loyalty_points_earned': loyalty_points_earned,
                'loyalty_points_used': loyalty_points_used,
                'discount_applied': f"${discount:.2f}",
            }
        )
        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [cust_email]
        )

    def handle_event(self, event):
        """Handle a generic/unknown/unexpected webhook event"""
        return HttpResponse(content=f'Unhandled event: {event["type"]}', status=200)

    def _extract_loyalty_points(self, intent):
        try:
            points = int(intent.metadata.get('loyalty_points_used', 0))
            return points
        except (ValueError, TypeError):
            return 0

    def handle_payment_intent_succeeded(self, event):
        intent = event.data.object
        pid = intent.id
        bag = intent.metadata.get('bag', '{}')
        loyalty_points_used = self._extract_loyalty_points(intent)
        save_info = intent.metadata.get('save_info', '')
        username = intent.metadata.get('username', 'AnonymousUser')

        try:
            order = Order.objects.get(stripe_pid=pid)
            return HttpResponse(
                content=f'Webhook received: {event["type"]} | SUCCESS: Order already processed',
                status=200
            )
        except Order.DoesNotExist:
            # Calculate base total from bag items
            bag_items = json.loads(bag)
            order_total = Decimal('0.00')
            
            for item_data in bag_items.values():
                product = Product.objects.get(sku=item_data['sku'])
                quantity = item_data.get('quantity', 0)
                item_price = product.price
                
                # Add attachment costs if any
                if 'attachments' in item_data and item_data['attachments']:
                    for attachment_sku in item_data['attachments']:
                        for attachment in ATTACHMENTS:
                            if attachment['sku'] == attachment_sku:
                                item_price += Decimal(str(attachment['price']))
                
                order_total += item_price * Decimal(str(quantity))

            # Calculate delivery
            delivery_cost = Decimal('10.00') if order_total < Decimal('100.00') else Decimal('0.00')
            
            # Calculate discount from loyalty points
            discount = Decimal(loyalty_points_used) * Decimal('0.1')
            grand_total = max(order_total + delivery_cost - discount, Decimal('0.00'))

            # Calculate points earned based on final total
            loyalty_points_earned = int(grand_total // 10)

            # Create or update order
            order, created = Order.objects.get_or_create(
                stripe_pid=pid,
                defaults={
                    'order_total': order_total,
                    'delivery_cost': delivery_cost,
                    'grand_total': grand_total,
                    'discount_applied': discount,
                    'loyalty_points_used': loyalty_points_used,
                    'loyalty_points': loyalty_points_earned,
                    'original_bag': bag
                }
            )

            if not created:
                order.order_total = order_total
                order.delivery_cost = delivery_cost
                order.grand_total = grand_total
                order.discount_applied = discount
                order.loyalty_points_used = loyalty_points_used
                order.loyalty_points = loyalty_points_earned
                order.save()

            try:
                # Create order line items
                for item_id, item_data in bag_items.items():
                    product = Product.objects.get(sku=item_data['sku'])
                    quantity = item_data.get('quantity', 0)
                    attachments = ','.join(item_data.get('attachments', []))

                    order_line_item = OrderLineItem(
                        order=order,
                        product=product,
                        quantity=quantity,
                        attachments=attachments
                    )
                    order_line_item.save()

                # Update user profile loyalty points
                if order.user_profile and created:
                    profile = order.user_profile
                    current_points = profile.loyalty_points

                    # Create REDEEM transaction if points were used
                    if loyalty_points_used > 0:
                        profile.points_transactions.create(
                            transaction_type='REDEEM',
                            points=-loyalty_points_used,
                            balance_before=current_points,
                            balance_after=max(0, current_points - loyalty_points_used),
                            order=order
                        )
                        current_points = max(0, current_points - loyalty_points_used)
                        profile.loyalty_points = current_points
                        profile.save()

                    # Create EARN transaction for points earned
                    if loyalty_points_earned > 0:
                        profile.points_transactions.create(
                            transaction_type='EARN',
                            points=loyalty_points_earned,
                            balance_before=current_points,
                            balance_after=current_points + loyalty_points_earned,
                            order=order
                        )
                        current_points += loyalty_points_earned
                        profile.loyalty_points = current_points
                        profile.save()

                # Send confirmation email
                self._send_confirmation_email(order, loyalty_points_earned, loyalty_points_used, discount)

            except Exception as e:
                order.delete()
                return HttpResponse(
                    content=f'Webhook received: {event["type"]} | ERROR: {e}',
                    status=500
                )

        return HttpResponse(
            content=f'Webhook received: {event["type"]} | SUCCESS: Created order in webhook',
            status=200
        )

    def handle_payment_intent_payment_failed(self, event):
        """Handle the payment_intent.payment_failed webhook from Stripe"""
        return HttpResponse(
            content=f'Webhook received: {event["type"]}',
            status=200
        )