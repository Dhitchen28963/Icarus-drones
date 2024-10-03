from decimal import Decimal
from django.conf import settings
from django.shortcuts import get_object_or_404
from products.models import Product
from products.constants import ATTACHMENTS


def get_attachment_name_by_sku(sku):
    """ Helper function to return the human-readable name of an attachment given its SKU """
    for attachment in ATTACHMENTS:
        if attachment['sku'] == sku:
            return attachment['name']
    return sku
    

def bag_contents(request):
    bag_items = []
    total = Decimal(0)
    product_count = 0
    bag = request.session.get('bag', {})

    print(f"Bag Contents: {bag}")

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
                attachment_names = [get_attachment_name_by_sku(att) for att in attachments]

                bag_items.append({
                    'item_id': item_id,
                    'quantity': quantity,
                    'product': product,
                    'attachments': attachment_names,  # Use human-readable names
                    'price': price,
                })
            except Product.DoesNotExist:
                print(f"Product not found for item_id: {item_id}")
                continue
        else:
            print(f"Invalid item in bag: {item_id} -> {item_data}")

    # Calculate delivery and grand total
    free_delivery_threshold = Decimal(str(settings.FREE_DELIVERY_THRESHOLD))
    if total < free_delivery_threshold:
        delivery = total * Decimal(str(settings.STANDARD_DELIVERY_PERCENTAGE)) / 100
        free_delivery_delta = free_delivery_threshold - total
    else:
        delivery = Decimal(0)
        free_delivery_delta = Decimal(0)

    grand_total = delivery + total

    context = {
        'bag_items': bag_items,
        'total': total,
        'product_count': product_count,
        'delivery': delivery,
        'free_delivery_delta': free_delivery_delta,
        'free_delivery_threshold': free_delivery_threshold,
        'grand_total': grand_total,
    }

    return context
