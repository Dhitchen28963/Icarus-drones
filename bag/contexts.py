from decimal import Decimal
from django.conf import settings
from django.shortcuts import get_object_or_404
from products.models import Product
from products.constants import ATTACHMENTS

def bag_contents(request):
    bag_items = []
    total = 0
    product_count = 0
    bag = request.session.get('bag', {})

    print(f"Bag Contents: {bag}")

    for item_id, item_data in bag.items():
        if isinstance(item_data, dict):  # Ensure item_data is a dictionary
            try:
                # If it's a regular product (with ID)
                if item_id.isdigit():
                    product = get_object_or_404(Product, pk=item_id)
                    price = item_data['price']
                else:
                    # For custom products with SKU and attachments
                    sku = item_data.get('sku')
                    if not sku:
                        continue
                    product = get_object_or_404(Product, sku=sku)
                    price = item_data['price']

                quantity = item_data['quantity']
                total += quantity * price
                product_count += quantity

                bag_items.append({
                    'item_id': item_id,
                    'quantity': quantity,
                    'product': product,
                    'attachments': item_data.get('attachments', []),
                    'price': price,
                })
            except Product.DoesNotExist:
                print(f"Product not found for item_id: {item_id}")
                continue
        else:
            print(f"Invalid item in bag: {item_id} -> {item_data}")

    # Calculate delivery and grand total
    if total < settings.FREE_DELIVERY_THRESHOLD:
        delivery = total * Decimal(settings.STANDARD_DELIVERY_PERCENTAGE / 100)
        free_delivery_delta = settings.FREE_DELIVERY_THRESHOLD - total
    else:
        delivery = 0
        free_delivery_delta = 0

    grand_total = delivery + total

    context = {
        'bag_items': bag_items,
        'total': total,
        'product_count': product_count,
        'delivery': delivery,
        'free_delivery_delta': free_delivery_delta,
        'free_delivery_threshold': settings.FREE_DELIVERY_THRESHOLD,
        'grand_total': grand_total,
    }

    return context
