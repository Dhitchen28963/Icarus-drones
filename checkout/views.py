from django.shortcuts import render, redirect, reverse, get_object_or_404
from django.contrib import messages
from django.conf import settings
from decimal import Decimal
import stripe
from .forms import OrderForm
from .models import Order, OrderLineItem
from products.models import Product
from products.constants import ATTACHMENTS
from bag.contexts import bag_contents

def get_attachment_name_by_sku(sku):
    """ Helper function to return the human-readable name of an attachment given its SKU """
    for attachment in ATTACHMENTS:
        if attachment['sku'] == sku:
            return attachment['name']
    return sku

def get_attachment_price_by_sku(sku):
    """ Helper function to return the price of an attachment given its SKU """
    for attachment in ATTACHMENTS:
        if attachment['sku'] == sku:
            return Decimal(attachment['price'])
    return Decimal(0)

def checkout(request):
    stripe_public_key = settings.STRIPE_PUBLIC_KEY
    stripe_secret_key = settings.STRIPE_SECRET_KEY

    bag = request.session.get('bag', {})
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

        if order_form.is_valid():
            # Save the order
            order = order_form.save()
            for item_id, item_data in bag.items():
                try:
                    # Check if the item_id is numeric (regular product)
                    if item_id.isdigit():
                        product = Product.objects.get(id=item_id)
                    else:
                        # Handle custom drone with SKU
                        product = Product.objects.get(sku=item_data['sku'])

                    # Calculate the final price including attachments
                    item_price = Decimal(str(item_data['price']))

                    # Add the prices of any attachments
                    if 'attachments' in item_data and item_data['attachments']:
                        for attachment_sku in item_data['attachments']:
                            attachment_price = get_attachment_price_by_sku(attachment_sku)
                            item_price += attachment_price

                    # Create the order line item
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
            total += item_data['quantity'] * Decimal(str(item_data['price']))

            if item_id.isdigit():
                product = get_object_or_404(Product, pk=item_id)
                item_data['product'] = product
                item_data['image'] = product.image.url if product.image else None
            else:
                if 'image' not in item_data or not item_data['image']:
                    item_data['image'] = '/media/custom1-black.webp' if 'falcon-x-10001-black' in item_id else '/media/noimage.webp'

                item_data['quantity'] = item_data.get('quantity', 1)

                try:
                    product = Product.objects.get(sku=item_data['sku'])
                    item_data['name'] = product.name
                except Product.DoesNotExist:
                    item_data['name'] = 'Custom Drone'

                # Handle attachments if any
                if 'attachments' in item_data and item_data['attachments']:
                    item_data['attachment_list'] = [get_attachment_name_by_sku(att) for att in item_data['attachments']]
                else:
                    item_data['attachment_list'] = []

            bag_items.append(item_data)

        # Calculate delivery, grand total, and Stripe total
        delivery = Decimal(10) if total < 100 else Decimal(0)
        grand_total = total + delivery
        stripe_total = round(grand_total * 100)
        stripe.api_key = stripe_secret_key

        # Create a Stripe payment intent
        intent = stripe.PaymentIntent.create(
            amount=stripe_total,
            currency=settings.STRIPE_CURRENCY,
        )

        # Loyalty points calculation
        loyalty_points_earned = int(total // 10)

        order_form = OrderForm()

        # Warning if Stripe public key is not set
        if not stripe_public_key:
            messages.warning(request, 'Stripe public key is missing. \
                Did you forget to set it in your environment?')

        context = {
            'order_form': order_form,
            'bag_items': bag_items,
            'total': total,
            'delivery': delivery,
            'grand_total': grand_total,
            'loyalty_points_earned': loyalty_points_earned,
            'product_count': sum(item['quantity'] for item in bag.values()),
            'stripe_public_key': stripe_public_key,
            'client_secret': intent.client_secret,
        }

        return render(request, 'checkout/checkout.html', context)


def checkout_success(request, order_number):
    """
    Handle successful checkouts
    """
    save_info = request.session.get('save_info')
    order = get_object_or_404(Order, order_number=order_number)
    messages.success(request, f'Order successfully processed! \
        Your order number is {order_number}. A confirmation \
        email will be sent to {order.email}.')

    if 'bag' in request.session:
        del request.session['bag']

    template = 'checkout/checkout_success.html'
    context = {
        'order': order,
    }

    return render(request, template, context)
