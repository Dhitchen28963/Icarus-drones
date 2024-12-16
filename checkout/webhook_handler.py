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


class StripeWH_Handler:
    """Handle Stripe webhooks"""

    def __init__(self, request):
        self.request = request
        self.mailchimp = Mailchimp()

    def _send_confirmation_email(self, order, loyalty_points_earned, loyalty_points_used, discount):
        try:
            print("\n========== EMAIL DEBUG INFORMATION ==========")
            print("Basic Order Info:")
            print(f"Order Number: {order.order_number}")
            print(f"Email: {order.email}")
            
            print("\nTotals:")
            print(f"Order Total: ${order.order_total}")
            print(f"Delivery Cost: ${order.delivery_cost}")
            print(f"Grand Total: ${order.grand_total}")
            print(f"Discount: ${discount:.2f}")
            
            print("\nLine Items in Order:")
            print(f"Total Line Items: {order.lineitems.count()}")
            for item in order.lineitems.all():
                print(f"\nLine Item Details:")
                print(f"- Product: {item.product.name}")
                print(f"  SKU: {item.product.sku}")
                print(f"  Quantity: {item.quantity}")
                print(f"  Base Price: ${item.product.price}")
                print(f"  Attachments: {item.attachments}")
                
            print("\nOriginal Bag Data:")
            try:
                bag_data = json.loads(order.original_bag)
                print(json.dumps(bag_data, indent=2))
            except:
                print("Could not parse original bag data")
            
            print("=========================================\n")

            print(f"Preparing to send confirmation email for order: {order.order_number}")
            print(f"Order email: {order.email}")
            print(f"Loyalty Points Earned: {loyalty_points_earned}, Used: {loyalty_points_used}")
            print(f"Discount Applied: ${discount:.2f}")

            background_image_url = "https://dhitchen28963-icarus-drones.s3.us-east-1.amazonaws.com/media/homepage_background.webp"
            facebook_icon_url = "https://dhitchen28963-icarus-drones.s3.us-east-1.amazonaws.com/media/facebook.png"
            twitter_icon_url = "https://dhitchen28963-icarus-drones.s3.us-east-1.amazonaws.com/media/twitter.png"
            instagram_icon_url = "https://dhitchen28963-icarus-drones.s3.us-east-1.amazonaws.com/media/instagram.png"

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
            }

            subject = render_to_string('checkout/confirmation_emails/confirmation_email_subject.txt', {'order': order}).strip()
            text_content = render_to_string('checkout/confirmation_emails/confirmation_email_body.txt', context)
            html_content = render_to_string('checkout/confirmation_emails/confirmation_email_body.html', context)

            print("Email subject and templates prepared.")

            msg = EmailMultiAlternatives(subject, text_content, settings.DEFAULT_FROM_EMAIL, [order.email])
            msg.attach_alternative(html_content, "text/html")
            msg.send()

            print(f"Confirmation email sent successfully to {order.email}")
        except Exception as e:
            print(f"Error sending email for order {order.order_number}: {e}")
            raise

    def handle_event(self, event):
        """Handle a generic/unknown/unexpected webhook event"""
        print(f"Unhandled event received: {event['type']}")
        return HttpResponse(content=f'Unhandled event: {event["type"]}', status=200)

    def _extract_loyalty_points(self, intent):
        try:
            points = int(intent.metadata.get('loyalty_points_used', 0))
            print(f"Extracted loyalty points: {points}")
            return points
        except (ValueError, TypeError):
            print("Error extracting loyalty points. Defaulting to 0.")
            return 0

    def handle_payment_intent_succeeded(self, event):
        print(f"Handling payment_intent.succeeded webhook for event ID: {event['id']}")
        try:
            intent = event.data.object
            pid = intent.id
            print(f"Payment Intent ID: {pid}")

            loyalty_points_used = self._extract_loyalty_points(intent)
            username = intent.metadata.get('username', 'AnonymousUser')
            print(f"Username from metadata: {username}")
            bag = intent.metadata.get('bag', '{}')
            print(f"Bag metadata: {bag}")

            try:
                order = Order.objects.get(stripe_pid=pid)
                print(f"Order found: {order.order_number}")

                if order.user_profile and order.loyalty_points_used > 0 and order.loyalty_points > 0:
                    print(f"Order {order.order_number} already processed with loyalty points.")
                    return HttpResponse(content=f'Webhook received: {event["type"]} | Order already processed', status=200)

                user_profile = order.user_profile
                if user_profile:
                    print("Adjusting loyalty points for user profile.")
                    with transaction.atomic():
                        user_profile.adjust_loyalty_points(
                            points_used=order.loyalty_points_used,
                            points_earned=order.loyalty_points,
                            order=order
                        )

                if not order.email:
                    print("Email not found in order. Extracting from intent.")
                    order.email = intent.charges.data[0].billing_details.email
                    order.save()

                self._send_confirmation_email(
                    order,
                    order.loyalty_points,
                    order.loyalty_points_used,
                    order.discount_applied
                )

                print(f"Webhook processed successfully for order: {order.order_number}")
                return HttpResponse(content=f'Webhook received: {event["type"]} | SUCCESS: Order processed', status=200)

            except Order.DoesNotExist:
                print(f"No order found for Payment Intent ID: {pid}")
                # Try up to 3 times with a small delay
                for attempt in range(3):
                    time.sleep(1)  # Wait 1 second
                    try:
                        order = Order.objects.get(stripe_pid=pid)
                        print(f"Order found on attempt {attempt + 1}: {order.order_number}")
                        
                        if order.user_profile and order.loyalty_points_used > 0 and order.loyalty_points > 0:
                            print(f"Order {order.order_number} already processed with loyalty points.")
                            return HttpResponse(content=f'Webhook received: {event["type"]} | Order already processed', status=200)

                        user_profile = order.user_profile
                        if user_profile:
                            print("Adjusting loyalty points for user profile.")
                            with transaction.atomic():
                                user_profile.adjust_loyalty_points(
                                    points_used=order.loyalty_points_used,
                                    points_earned=order.loyalty_points,
                                    order=order
                                )

                        if not order.email:
                            print("Email not found in order. Extracting from intent.")
                            order.email = intent.charges.data[0].billing_details.email
                            order.save()

                        self._send_confirmation_email(
                            order,
                            order.loyalty_points,
                            order.loyalty_points_used,
                            order.discount_applied
                        )

                        print(f"Webhook processed successfully for order: {order.order_number}")
                        return HttpResponse(content=f'Webhook received: {event["type"]} | SUCCESS: Order processed', status=200)
                        
                    except Order.DoesNotExist:
                        print(f"Order still not found on attempt {attempt + 1}")
                        continue
                
                print("All retry attempts failed, creating new order")
                # Process new order if not found
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
                                    item_price += Decimal(str(attachment['price']))

                    order_total += item_price * Decimal(str(quantity))

                delivery_cost = Decimal('10.00') if order_total < Decimal('100.00') else Decimal('0.00')
                discount = Decimal(loyalty_points_used) * Decimal('0.1')
                grand_total = max(order_total + delivery_cost - discount, Decimal('0.00'))
                loyalty_points_earned = int(grand_total // 10)

                print(f"Order Total: {order_total}, Grand Total: {grand_total}, Loyalty Points Earned: {loyalty_points_earned}")

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
                
                if created:  # Only create line items if this is a new order
                    print("\nDEBUG - Creating Line Items:")
                    print(f"Bag items to process: {bag_items}")
                    for item_id, item_data in bag_items.items():
                        product = Product.objects.get(sku=item_data['sku'])
                        quantity = item_data.get('quantity', 0)
                        attachments = ','.join(item_data.get('attachments', []))

                        print(f"Creating line item for product: {product.name}")
                        print(f"SKU: {product.sku}, Quantity: {quantity}")
                        print(f"Attachments: {attachments}")

                        order_line_item = OrderLineItem(
                            order=order,
                            product=product,
                            quantity=quantity,
                            attachments=attachments
                        )
                        order_line_item.save()
                        print(f"Line item saved: {order_line_item.id}")

                    print("Line item creation complete\n")

                self._send_confirmation_email(order, loyalty_points_earned, loyalty_points_used, discount)

                print(f"New order created and processed successfully for Payment Intent ID: {pid}")
                return HttpResponse(content=f'Webhook received: {event["type"]} | SUCCESS', status=200)

        except Exception as e:
            print(f"Error processing webhook: {e}")
            return HttpResponse(content=f'Error: {str(e)}', status=500)

    def handle_payment_intent_payment_failed(self, event):
        """Handle the payment_intent.payment_failed webhook from Stripe"""
        print(f"Payment failed for event ID: {event['id']}")
        return HttpResponse(content=f'Webhook received: {event["type"]}', status=200)