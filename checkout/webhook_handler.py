import logging
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

logger = logging.getLogger(__name__)

class StripeWH_Handler:
    """Handle Stripe webhooks"""

    def __init__(self, request):
        self.request = request
        self.mailchimp = Mailchimp()

    def _send_confirmation_email(self, order, loyalty_points_earned, loyalty_points_used, discount):
        try:
            print(f"Order Line Items Count: {order.lineitems.count()}")
            for line_item in order.lineitems.all():
                print(f"Product: {line_item.product.name}, Quantity: {line_item.quantity}, Total: {line_item.lineitem_total}")
            print(f"Order Total: {order.order_total}, Delivery: {order.delivery_cost}, Discount: {discount}, Grand Total: {order.grand_total}")
        
            print("Using confirmation_email_body.html template for email content.")
            print(f"Site URL: {settings.SITE_URL}")
            
            logger.debug("\nLine Items in Order:")
            logger.debug(f"Total Line Items: {order.lineitems.count()}")
            for item in order.lineitems.all():
                logger.debug(f"\nLine Item Details:")
                logger.debug(f"- Product: {item.product.name}")
                logger.debug(f"  SKU: {item.product.sku}")
                logger.debug(f"  Quantity: {item.quantity}")
                logger.debug(f"  Base Price: ${item.product.price}")
                logger.debug(f"  Attachments: {item.attachments}")
                
            logger.debug("\nOriginal Bag Data:")
            try:
                bag_data = json.loads(order.original_bag)
                logger.debug(json.dumps(bag_data, indent=2))
            except:
                logger.debug("Could not parse original bag data")
            
            logger.debug("=========================================\n")

            logger.info(f"Preparing to send confirmation email for order: {order.order_number}")
            logger.info(f"Order email: {order.email}")
            logger.info(f"Loyalty Points Earned: {loyalty_points_earned}, Used: {loyalty_points_used}")
            logger.info(f"Discount Applied: ${discount:.2f}")

            background_image_url = "https://dhitchen28963-icarus-drones.s3.us-east-1.amazonaws.com/media/homepage_background.webp"
            facebook_icon_url = "https://dhitchen28963-icarus-drones.s3.us-east-1.amazonaws.com/media/facebook.png"
            twitter_icon_url = "https://dhitchen28963-icarus-drones.s3.us-east-1.amazonaws.com/media/twitter.png"
            instagram_icon_url = "https://dhitchen28963-icarus-drones.s3.us-east-1.amazonaws.com/media/instagram.png"

            # Add the unsubscribe URL
            unsubscribe_url = f"{settings.SITE_URL}/profiles/unsubscribe/{order.email}/"

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
            }

            print(f"Email Context Data: {context}")

            subject = render_to_string('checkout/confirmation_emails/confirmation_email_subject.txt', {'order': order}).strip()
            text_content = render_to_string('checkout/confirmation_emails/confirmation_email_body.txt', context)
            html_content = render_to_string('checkout/confirmation_emails/confirmation_email_body.html', context)

            logger.debug("Email subject and templates prepared.")

            msg = EmailMultiAlternatives(subject, text_content, settings.DEFAULT_FROM_EMAIL, [order.email])
            msg.attach_alternative(html_content, "text/html")
            msg.send()

            logger.info(f"Confirmation email sent successfully to {order.email}")
        except Exception as e:
            logger.exception(f"Error sending email for order {order.order_number}: {e}")
            raise


    def handle_event(self, event):
        """Handle a generic/unknown/unexpected webhook event"""
        logger.warning(f"Unhandled event received: {event['type']}")
        return HttpResponse(content=f'Unhandled event: {event["type"]}', status=200)

    def _extract_loyalty_points(self, intent):
        try:
            points = int(intent.metadata.get('loyalty_points_used', 0))
            logger.debug(f"Extracted loyalty points: {points}")
            return points
        except (ValueError, TypeError):
            logger.warning("Error extracting loyalty points. Defaulting to 0.")
            return 0

    def handle_payment_intent_succeeded(self, event):
        logger.info(f"Handling payment_intent.succeeded webhook for event ID: {event['id']}")
        try:
            intent = event.data.object
            pid = intent.id
            logger.info(f"Payment Intent ID: {pid}")

            loyalty_points_used = self._extract_loyalty_points(intent)
            username = intent.metadata.get('username', 'AnonymousUser')
            logger.info(f"Username from metadata: {username}")
            bag = intent.metadata.get('bag', '{}')
            logger.info(f"Bag metadata: {bag}")

            try:
                order = Order.objects.get(stripe_pid=pid)
                logger.info(f"Order found: {order.order_number}")

                if order.user_profile and order.loyalty_points_used > 0 and order.loyalty_points > 0:
                    logger.info(f"Order {order.order_number} already processed with loyalty points.")
                    return HttpResponse(content=f'Webhook received: {event["type"]} | Order already processed', status=200)

                user_profile = order.user_profile
                if user_profile:
                    logger.info("Adjusting loyalty points for user profile.")
                    with transaction.atomic():
                        user_profile.adjust_loyalty_points(
                            points_used=order.loyalty_points_used,
                            points_earned=order.loyalty_points,
                            order=order
                        )

                if not order.email:
                    logger.info("Email not found in order. Extracting from intent.")
                    order.email = intent.charges.data[0].billing_details.email
                    order.save()

                self._send_confirmation_email(
                    order,
                    order.loyalty_points,
                    order.loyalty_points_used,
                    order.discount_applied
                )

                logger.info(f"Webhook processed successfully for order: {order.order_number}")
                return HttpResponse(content=f'Webhook received: {event["type"]} | SUCCESS: Order processed', status=200)

            except Order.DoesNotExist:
                logger.warning(f"No order found for Payment Intent ID: {pid}")
                # Try up to 3 times with a small delay
                for attempt in range(3):
                    time.sleep(1)  # Wait 1 second
                    try:
                        order = Order.objects.get(stripe_pid=pid)
                        logger.info(f"Order found on attempt {attempt + 1}: {order.order_number}")
                        
                        if order.user_profile and order.loyalty_points_used > 0 and order.loyalty_points > 0:
                            logger.info(f"Order {order.order_number} already processed with loyalty points.")
                            return HttpResponse(content=f'Webhook received: {event["type"]} | Order already processed', status=200)

                        user_profile = order.user_profile
                        if user_profile:
                            logger.info("Adjusting loyalty points for user profile.")
                            with transaction.atomic():
                                user_profile.adjust_loyalty_points(
                                    points_used=order.loyalty_points_used,
                                    points_earned=order.loyalty_points,
                                    order=order
                                )

                        if not order.email:
                            logger.info("Email not found in order. Extracting from intent.")
                            order.email = intent.charges.data[0].billing_details.email
                            order.save()

                        self._send_confirmation_email(
                            order,
                            order.loyalty_points,
                            order.loyalty_points_used,
                            order.discount_applied
                        )

                        logger.info(f"Webhook processed successfully for order: {order.order_number}")
                        return HttpResponse(content=f'Webhook received: {event["type"]} | SUCCESS: Order processed', status=200)
                        
                    except Order.DoesNotExist:
                        logger.warning(f"Order still not found on attempt {attempt + 1}")
                        continue
                
                logger.info("All retry attempts failed, creating new order")
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

                logger.info(f"Order Total: {order_total}, Grand Total: {grand_total}, Loyalty Points Earned: {loyalty_points_earned}")

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
                    logger.debug("\nDEBUG - Creating Line Items:")
                    logger.debug(f"Bag items to process: {bag_items}")
                    for item_id, item_data in bag_items.items():
                        product = Product.objects.get(sku=item_data['sku'])
                        quantity = item_data.get('quantity', 0)
                        attachments = ','.join(item_data.get('attachments', []))

                        logger.debug(f"Creating line item for product: {product.name}")
                        logger.debug(f"SKU: {product.sku}, Quantity: {quantity}")
                        logger.debug(f"Attachments: {attachments}")

                        order_line_item = OrderLineItem(
                            order=order,
                            product=product,
                            quantity=quantity,
                            attachments=attachments
                        )
                        print(f"Saving line item for product: {product.name}, Quantity: {item_data['quantity']}, Attachments: {item_data.get('attachments', [])}")
                        order_line_item.save()
                        logger.debug(f"Line item saved: {order_line_item.id}")

                    logger.debug("Line item creation complete\n")

                self._send_confirmation_email(order, loyalty_points_earned, loyalty_points_used, discount)

                logger.info(f"New order created and processed successfully for Payment Intent ID: {pid}")
                return HttpResponse(content=f'Webhook received: {event["type"]} | SUCCESS', status=200)

        except Exception as e:
            logger.exception(f"Error processing webhook: {e}")
            return HttpResponse(content=f'Error: {str(e)}', status=500)

    def handle_payment_intent_payment_failed(self, event):
        """Handle the payment_intent.payment_failed webhook from Stripe"""
        logger.warning(f"Payment failed for event ID: {event['id']}")
        return HttpResponse(content=f'Webhook received: {event["type"]}', status=200)