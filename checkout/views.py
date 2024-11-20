from django.shortcuts import render, redirect, reverse, get_object_or_404, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.conf import settings
from decimal import Decimal
import stripe
import json
import os
from .forms import OrderForm
from .models import Order, OrderLineItem
from products.models import Product
from profiles.models import UserProfile
from profiles.forms import UserProfileForm
from products.constants import ATTACHMENTS
from bag.contexts import bag_contents

# Helper functions for attachments
def get_attachment_name_by_sku(sku):
    for attachment in ATTACHMENTS:
        if attachment['sku'] == sku:
            return attachment['name']
    return sku

def get_attachment_price_by_sku(sku):
    for attachment in ATTACHMENTS:
        if attachment['sku'] == sku:
            return Decimal(attachment['price'])
    return Decimal(0)


@require_POST
def cache_checkout_data(request):
    try:
        client_secret = request.POST.get('client_secret')
        loyalty_points_used = int(request.POST.get('loyalty_points', 0))

        if client_secret:
            pid = client_secret.split('_secret')[0]
            stripe.api_key = settings.STRIPE_SECRET_KEY

            # Calculate the new total with loyalty points discount
            payment_intent = stripe.PaymentIntent.retrieve(pid)
            original_amount = payment_intent.amount
            discount_amount = loyalty_points_used * 10
            new_amount = max(original_amount - discount_amount, 0)

            condensed_bag = {
                item_id: {
                    "quantity": item_data.get("quantity"),
                    "sku": item_data.get("sku", "N/A")
                }
                for item_id, item_data in request.session.get('bag', {}).items()
            }

            bag_metadata = json.dumps(condensed_bag)
            if len(bag_metadata) > 500:
                for item_id in list(condensed_bag):
                    condensed_bag.pop(item_id)
                    bag_metadata = json.dumps(condensed_bag)
                    if len(bag_metadata) <= 500:
                        break

            # Update the payment intent with new amount and metadata
            stripe.PaymentIntent.modify(
                pid,
                amount=new_amount,
                metadata={
                    'bag': bag_metadata,
                    'save_info': request.POST.get('save_info'),
                    'username': str(request.user),
                    'loyalty_points_used': str(loyalty_points_used),
                    'original_amount': str(original_amount),
                    'discount_amount': str(discount_amount)
                }
            )

        return HttpResponse(status=200)
    except Exception as e:
        messages.error(request, 'Sorry, your payment cannot be processed right now. Please try again later.')
        return HttpResponse(content=e, status=400)

def checkout(request):
    stripe_public_key = settings.STRIPE_PUBLIC_KEY
    stripe_secret_key = settings.STRIPE_SECRET_KEY

    bag = request.session.get('bag', {})
    serialized_bag = {}
    for item_id, item_data in bag.items():
        serialized_item_data = {
            "quantity": item_data.get("quantity"),
            "price": str(item_data["price"]),
            "attachments": item_data.get("attachments", []),
            "sku": item_data.get("sku")
        }
        serialized_bag[item_id] = serialized_item_data

    if not bag:
        messages.error(request, "There's nothing in your bag at the moment")
        return redirect(reverse('products'))

    # Fetch user profile and loyalty points
    user_loyalty_points = 0
    profile = None
    if request.user.is_authenticated:
        try:
            profile = UserProfile.objects.get(user=request.user)
            user_loyalty_points = profile.loyalty_points
        except UserProfile.DoesNotExist:
            pass

    if request.method == 'POST':
        form_data = {
            'full_name': request.POST['full_name'],
            'email': request.POST['email'],
            'phone_number': request.POST['phone_number'],
            'country': request.POST['country'],
            'postcode': request.POST['postcode'],
            'town_or_city': request.POST['town_or_city'],
            'street_address1': request.POST['street_address1'],
            'street_address2': request.POST['street_address2'],
            'county': request.POST['county'],
        }
        order_form = OrderForm(form_data)
        client_secret = request.POST.get('client_secret')
        loyalty_points_used = int(request.POST.get('loyalty_points', 0))

        # Ensure valid loyalty points
        if loyalty_points_used < 0 or loyalty_points_used > user_loyalty_points:
            messages.error(request, "Invalid loyalty points. Points must be between 0 and your available points.")
            return redirect(reverse('checkout'))

        # Store applied loyalty points in session
        request.session['loyalty_points'] = loyalty_points_used

        # Calculate order totals
        order_total = Decimal('0.00')
        for item_id, item_data in bag.items():
            product = Product.objects.get(sku=item_data['sku'])
            quantity = item_data.get('quantity', 1)
            price = product.price

            # Add attachment costs
            if 'attachments' in item_data and item_data['attachments']:
                for attachment_sku in item_data['attachments']:
                    for attachment in ATTACHMENTS:
                        if attachment['sku'] == attachment_sku:
                            price += Decimal(str(attachment['price']))

            order_total += price * Decimal(str(quantity))

        delivery_cost = Decimal('10.00') if order_total < Decimal('100.00') else Decimal('0.00')
        discount = Decimal(loyalty_points_used) * Decimal('0.1')
        grand_total = max(order_total + delivery_cost - discount, Decimal('0.00'))
        stripe_total = round(grand_total * 100)

        # Calculate loyalty points earned based on grand total
        points_earned = int(grand_total // 10)

        if not client_secret:
            messages.error(request, 'There was an issue with the payment process. Please try again.')
            return redirect(reverse('checkout'))

        if order_form.is_valid():
            order = order_form.save(commit=False)
            pid = client_secret.split('_secret')[0]
            order.stripe_pid = pid
            order.original_bag = json.dumps(serialized_bag)
            order.order_total = order_total
            order.delivery_cost = delivery_cost
            order.discount_applied = discount
            order.grand_total = grand_total
            order.loyalty_points = points_earned
            order.loyalty_points_used = loyalty_points_used
            order.save()

            # Create order line items
            for item_id, item_data in bag.items():
                try:
                    product = Product.objects.get(sku=item_data['sku'])
                    order_line_item = OrderLineItem(
                        order=order,
                        product=product,
                        quantity=item_data['quantity'],
                        attachments=','.join(item_data.get('attachments', []))
                    )
                    order_line_item.save()
                except Product.DoesNotExist:
                    messages.error(request, "One of the products wasn't found in our database. Please call us for assistance!")
                    order.delete()
                    return redirect(reverse('view_bag'))

            # Update loyalty points
            if request.user.is_authenticated and profile:
                profile.loyalty_points = max(0, profile.loyalty_points - loyalty_points_used + points_earned)
                profile.save()

            # Redirect to success page
            request.session['save_info'] = 'save-info' in request.POST
            return redirect(reverse('checkout_success', args=[order.order_number]))
        else:
            messages.error(request, 'There was an error with your form. Please double-check your information.')

    else:
        total = Decimal('0.00')
        bag_items = []

        for item_id, item_data in bag.items():
            product = get_object_or_404(Product, sku=item_data['sku'])
            quantity = item_data.get('quantity', 1)
            price = product.price

            # Calculate price with attachments
            if 'attachments' in item_data and item_data['attachments']:
                for attachment_sku in item_data['attachments']:
                    for attachment in ATTACHMENTS:
                        if attachment['sku'] == attachment_sku:
                            price += Decimal(str(attachment['price']))

            total += price * Decimal(str(quantity))

            item_data.update({
                'name': product.name,
                'image': f"/media/{product.image}" if product.image else '/media/noimage.webp',
                'attachment_list': [get_attachment_name_by_sku(att) for att in item_data.get('attachments', [])]
            })
            bag_items.append(item_data)

        delivery_cost = Decimal('10.00') if total < Decimal('100.00') else Decimal('0.00')
        loyalty_points_used = int(request.session.get('loyalty_points', 0))
        discount = Decimal(loyalty_points_used) * Decimal('0.1')
        grand_total = max(total + delivery_cost - discount, Decimal('0.00'))
        stripe_total = round(grand_total * 100)  # Use discounted total for Stripe
        loyalty_points_earned = int(grand_total // 10)

        stripe.api_key = stripe_secret_key
        intent = stripe.PaymentIntent.create(
            amount=stripe_total,  # Your existing amount calculation
            currency=settings.STRIPE_CURRENCY,
            payment_method_types=['card'],
            capture_method='automatic',
            confirm=False,  # Important: Don't confirm automatically
            metadata={
                'bag': json.dumps(serialized_bag),
                'save_info': request.POST.get('save_info', ''),
                'username': request.user.username if request.user.is_authenticated else 'AnonymousUser',
                'loyalty_points_used': str(loyalty_points_used),
            }
        )

        # Prefill order form for authenticated users
        order_form = OrderForm()
        if request.user.is_authenticated and profile:
            order_form = OrderForm(initial={
                'full_name': profile.full_name,
                'email': request.user.email,
                'phone_number': profile.default_phone_number,
                'country': profile.default_country,
                'postcode': profile.default_postcode,
                'town_or_city': profile.default_town_or_city,
                'street_address1': profile.default_street_address1,
                'street_address2': profile.default_street_address2,
                'county': profile.default_county,
            })

        # Warn if Stripe public key is missing
        if not stripe_public_key:
            messages.warning(request, 'Stripe public key is missing. Did you forget to set it in your environment?')

        context = {
            'order_form': order_form,
            'bag_items': bag_items,
            'total': total,
            'delivery': delivery_cost,
            'grand_total': grand_total,
            'loyalty_points_earned': loyalty_points_earned,
            'user_loyalty_points': user_loyalty_points,
            'loyalty_points_used': loyalty_points_used,
            'product_count': sum(item['quantity'] for item in bag.values()),
            'stripe_public_key': stripe_public_key,
            'client_secret': intent.client_secret,
        }

        return render(request, 'checkout/checkout.html', context)


def checkout_success(request, order_number):
    save_info = request.session.get('save_info')
    order = get_object_or_404(Order, order_number=order_number)
    messages.success(request, f'Order successfully processed! Your order number is {order_number}. A confirmation email will be sent to {order.email}.')

    # Clear the bag session
    if 'bag' in request.session:
        del request.session['bag']
    if 'loyalty_points' in request.session:
        del request.session['loyalty_points']

    # If user is authenticated, update profile and loyalty points
    loyalty_points_earned = 0
    discount_applied = Decimal(order.loyalty_points_used) * Decimal('0.1')  # Calculate discount from used loyalty points
    if request.user.is_authenticated:
        profile = UserProfile.objects.get(user=request.user)
        order.user_profile = profile
        order.save()

        # Calculate loyalty points
        total_amount = Decimal(order.grand_total)
        loyalty_points_earned = int(total_amount // 10)
        
        # Update profile loyalty points with proper transaction tracking
        current_points = profile.loyalty_points
        
        # First deduct points if any were used
        if order.loyalty_points_used > 0:
            profile.loyalty_points = max(0, current_points - order.loyalty_points_used)
            profile.save()
            # Create redemption transaction
            profile.points_transactions.create(
                transaction_type='REDEEM',
                points=-order.loyalty_points_used,
                balance_before=current_points,
                balance_after=profile.loyalty_points,
                order=order
            )
            current_points = profile.loyalty_points

        # Then add earned points
        if loyalty_points_earned > 0:
            profile.loyalty_points = current_points + loyalty_points_earned
            profile.save()
            # Create earning transaction
            profile.points_transactions.create(
                transaction_type='EARN',
                points=loyalty_points_earned,
                balance_before=current_points,
                balance_after=profile.loyalty_points,
                order=order
            )

        # Save user profile info if 'save_info' option was selected
        if save_info:
            profile.default_phone_number = order.phone_number
            profile.default_country = order.country
            profile.default_postcode = order.postcode
            profile.default_town_or_city = order.town_or_city
            profile.default_street_address1 = order.street_address1
            profile.default_street_address2 = order.street_address2
            profile.default_county = order.county
            profile.save()

        # Add success messages for loyalty points
        if order.loyalty_points_used > 0:
            messages.success(request, f"You redeemed {order.loyalty_points_used} loyalty points for this purchase, saving ${discount_applied:.2f}.")
        if loyalty_points_earned > 0:
            messages.success(request, f"You earned {loyalty_points_earned} loyalty points for this order.")

    context = {
        'order': order,
        'loyalty_points_earned': loyalty_points_earned,
        'discount_applied': discount_applied.quantize(Decimal('0.01')),  # Ensure correct formatting
        'loyalty_points_used': order.loyalty_points_used,
    }
    return render(request, 'checkout/checkout_success.html', context)