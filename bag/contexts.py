from decimal import Decimal
from django.conf import settings
from django.shortcuts import get_object_or_404
from products.models import Product
from products.constants import ATTACHMENTS
from profiles.models import UserProfile


def get_attachment_name_by_sku(sku):
    """Helper function to return human-readable name of an attachment"""
    for attachment in ATTACHMENTS:
        if attachment['sku'] == sku:
            return attachment['name']
    return sku


def bag_contents(request):
    bag_items = []
    total = Decimal(0)
    product_count = 0
    bag = request.session.get('bag', {})
    loyalty_points_used = Decimal(0)
    loyalty_discount = Decimal(0)
    user_loyalty_points = 0

    # If user is authenticated, get their loyalty points
    if request.user.is_authenticated:
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            user_loyalty_points = user_profile.loyalty_points
        except UserProfile.DoesNotExist:
            user_loyalty_points = 0

    for item_id, item_data in bag.items():
        if isinstance(item_data, dict):
            try:
                if item_id.isdigit():
                    product = get_object_or_404(Product, pk=item_id)
                    price = Decimal(str(item_data['price']))
                else:
                    # For custom products with SKU and attachments
                    sku = item_data.get('sku')
                    if not sku:
                        continue
                    product = get_object_or_404(Product, sku=sku)
                    price = Decimal(str(item_data['price']))

                quantity = item_data['quantity']
                total += quantity * price
                product_count += quantity

                # Convert attachment SKUs to human-readable names
                attachments = item_data.get('attachments', [])
                attachment_names = [
                    get_attachment_name_by_sku(att) for att in attachments
                ]

                bag_items.append({
                    'item_id': item_id,
                    'quantity': quantity,
                    'product': product,
                    'attachments': attachment_names,
                    'price': price,
                })
            except Product.DoesNotExist:
                continue
        else:
            continue

    # Calculate delivery and grand total
    free_delivery_threshold = Decimal(str(settings.FREE_DELIVERY_THRESHOLD))
    if total < free_delivery_threshold:
        delivery = (total *
                    Decimal(str(settings.STANDARD_DELIVERY_PERCENTAGE)) / 100)
        free_delivery_delta = free_delivery_threshold - total
    else:
        delivery = Decimal(0)
        free_delivery_delta = Decimal(0)

    grand_total = delivery + total

    # Apply loyalty points discount
    if 'loyalty_points' in request.session:
        loyalty_points_used = Decimal(request.session.get('loyalty_points', 0))
        loyalty_discount = loyalty_points_used * Decimal(0.1)
        grand_total = max(grand_total - loyalty_discount, Decimal(0))

    context = {
        'bag_items': bag_items,
        'total': total,
        'product_count': product_count,
        'delivery': delivery,
        'free_delivery_delta': free_delivery_delta,
        'free_delivery_threshold': free_delivery_threshold,
        'grand_total': grand_total,
        'loyalty_points_used': loyalty_points_used,
        'loyalty_discount': loyalty_discount,
        'user_loyalty_points': user_loyalty_points,
    }

    return context
