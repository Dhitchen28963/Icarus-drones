from django.shortcuts import render, redirect, reverse, get_object_or_404, HttpResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.conf import settings
from decimal import Decimal
import stripe
import json
import os
from .forms import OrderForm
from .models import Order, OrderLineItem
from products.models import Product
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
        if client_secret:
            pid = client_secret.split('_secret')[0]
            stripe.api_key = settings.STRIPE_SECRET_KEY

            # Simplify the bag metadata for Stripe
            simplified_bag = {
                item_id: {
                    "quantity": item_data.get("quantity"),
                    "sku": item_data.get("sku", "N/A")
                }
                for item_id, item_data in request.session.get('bag', {}).items()
            }

            # Send simplified metadata to Stripe
            stripe.PaymentIntent.modify(pid, metadata={
                'bag': json.dumps(simplified_bag),
                'save_info': request.POST.get('save_info'),
                'username': str(request.user),
            })
        return HttpResponse(status=200)
    except Exception as e:
        messages.error(request, 'Sorry, your payment cannot be processed right now. Please try again later.')
        return HttpResponse(content=e, status=400)

def checkout(request):
    stripe_public_key = settings.STRIPE_PUBLIC_KEY
    stripe_secret_key = settings.STRIPE_SECRET_KEY

    # Serialize bag contents to ensure JSON compatibility
    bag = request.session.get('bag', {})
    serialized_bag = {}
    for item_id, item_data in bag.items():
        serialized_item_data = {
            "quantity": item_data.get("quantity"),
            "price": str(item_data["price"]),
            "attachments": item_data.get("attachments", [])
        }
        if item_id.isdigit():
            serialized_bag[item_id] = serialized_item_data
        else:
            serialized_item_data["sku"] = item_data.get("sku")
            serialized_bag[item_id] = serialized_item_data

    if not bag:
        messages.error(request, "There's nothing in your bag at the moment")
        return redirect(reverse('products'))

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

        if not client_secret:
            messages.error(request, 'There was an issue with the payment process. Please try again.')
            return redirect(reverse('checkout'))

        if order_form.is_valid():
            order = order_form.save(commit=False)
            pid = client_secret.split('_secret')[0]
            order.stripe_pid = pid
            order.original_bag = json.dumps(serialized_bag)
            order.save()
            for item_id, item_data in bag.items():
                try:
                    if item_id.isdigit():
                        product = Product.objects.get(id=item_id)
                        order_line_item = OrderLineItem(
                            order=order,
                            product=product,
                            quantity=item_data['quantity'],
                        )
                        order_line_item.save()
                    else:
                        product = Product.objects.get(sku=item_data['sku'])
                        item_price = Decimal(str(item_data['price']))

                        if 'attachments' in item_data and item_data['attachments']:
                            for attachment_sku in item_data['attachments']:
                                attachment_price = get_attachment_price_by_sku(attachment_sku)
                                item_price += attachment_price

                        order_line_item = OrderLineItem(
                            order=order,
                            product=product,
                            quantity=item_data['quantity'],
                            attachments=','.join(item_data['attachments']) if 'attachments' in item_data else None,
                        )
                        order_line_item.save()
                except Product.DoesNotExist:
                    messages.error(request, (
                        "One of the products in your bag wasn't found in our database. "
                        "Please call us for assistance!")
                    )
                    order.delete()
                    return redirect(reverse('view_bag'))

            request.session['save_info'] = 'save-info' in request.POST
            return redirect(reverse('checkout_success', args=[order.order_number]))
        else:
            messages.error(request, 'There was an error with your form. Please double-check your information.')

    else:
        bag_items = []
        total = Decimal(0)

        for item_id, item_data in bag.items():
            quantity = item_data.get('quantity', 1)
            total += quantity * Decimal(str(item_data['price']))

            if item_id.isdigit():
                product = get_object_or_404(Product, pk=item_id)
                item_data['product'] = {
                    "id": product.id,
                    "name": product.name,
                    "price": str(product.price),
                }
                item_data['image'] = product.image.url if product.image else None
            else:
                custom_type = "custom1" if "falcon" in item_data['sku'] else (
                    "custom2" if "sky-hawk" in item_data['sku'] else "custom3"
                )
                color = item_data['sku'].split('-')[-1]
                custom_image_path = f'/media/{custom_type}-{color}.webp'

                if os.path.isfile(os.path.join(settings.MEDIA_ROOT, f'{custom_type}-{color}.webp')):
                    item_data['image'] = custom_image_path
                else:
                    item_data['image'] = '/media/noimage.webp'

                item_data['quantity'] = quantity
                try:
                    product = Product.objects.get(sku=item_data['sku'])
                    item_data['name'] = product.name
                except Product.DoesNotExist:
                    item_data['name'] = 'Custom Drone'

                if 'attachments' in item_data and item_data['attachments']:
                    item_data['attachment_list'] = [get_attachment_name_by_sku(att) for att in item_data['attachments']]
                else:
                    item_data['attachment_list'] = []

            bag_items.append(item_data)

        delivery = Decimal(10) if total < 100 else Decimal(0)
        grand_total = total + delivery
        stripe_total = round(grand_total * 100)
        stripe.api_key = stripe_secret_key

        intent = stripe.PaymentIntent.create(
            amount=stripe_total,
            currency=settings.STRIPE_CURRENCY,
        )
        client_secret = intent.client_secret

        loyalty_points_earned = int(total // 10)
        product_count = sum(item['quantity'] for item in bag.values())

        order_form = OrderForm()

        if not stripe_public_key:
            messages.warning(request, 'Stripe public key is missing. Did you forget to set it in your environment?')

        context = {
            'order_form': order_form,
            'bag_items': bag_items,
            'total': total,
            'delivery': delivery,
            'grand_total': grand_total,
            'loyalty_points_earned': loyalty_points_earned,
            'product_count': product_count,
            'stripe_public_key': stripe_public_key,
            'client_secret': client_secret,
        }

        return render(request, 'checkout/checkout.html', context)

def checkout_success(request, order_number):
    save_info = request.session.get('save_info')
    order = get_object_or_404(Order, order_number=order_number)
    messages.success(request, f'Order successfully processed! Your order number is {order_number}. A confirmation email will be sent to {order.email}.')

    if 'bag' in request.session:
        del request.session['bag']

    template = 'checkout/checkout_success.html'
    context = {
        'order': order,
    }
    return render(request, template, context)
