from django.shortcuts import render, redirect, reverse, get_object_or_404
from django.contrib import messages
from decimal import Decimal
from .forms import OrderForm
from products.models import Product  # Import Product to handle image fetching
from products.constants import ATTACHMENTS  # Assuming you are using ATTACHMENTS in your project

def get_attachment_name_by_sku(sku):
    """ Helper function to return the human-readable name of an attachment given its SKU """
    for attachment in ATTACHMENTS:
        if attachment['sku'] == sku:
            return attachment['name']
    return sku

def checkout(request):
    bag = request.session.get('bag', {})
    
    if not bag:
        messages.error(request, "There's nothing in your bag at the moment")
        return redirect(reverse('products'))

    # Prepare bag items for the template
    bag_items = []
    total = Decimal(0)
    
    for item_id, item_data in bag.items():
        total += item_data['quantity'] * Decimal(str(item_data['price']))
        
        # Handle regular products with numeric IDs
        if item_id.isdigit():
            product = get_object_or_404(Product, pk=item_id)
            item_data['product'] = product
            item_data['image'] = product.image.url if product.image else None
        else:
            # Handle custom drones, where image is already in item_data or needs to be set
            if 'image' not in item_data or not item_data['image']:
                # Assign the image manually if it's missing
                item_data['image'] = '/media/custom1-black.webp' if 'falcon-x-10001-black' in item_id else '/media/noimage.webp'

            # Ensure the quantity is set for custom drones
            item_data['quantity'] = item_data.get('quantity', 1)

            # Add logic to handle custom drone names and attachments
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

            # Debug statement to check image URL and item name
            print(f"Item ID: {item_id}, Image URL: {item_data.get('image')}, Name: {item_data.get('name')}")

        bag_items.append(item_data)

    # Delivery fee (example: free delivery over 100, otherwise 10)
    delivery = Decimal(10) if total < 100 else Decimal(0)
    grand_total = total + delivery

    # Loyalty points calculation
    loyalty_points_earned = int(total // 10)

    # Render the form
    order_form = OrderForm()

    context = {
        'order_form': order_form,
        'bag_items': bag_items,  # Use the prepared bag_items
        'total': total,
        'delivery': delivery,
        'grand_total': grand_total,
        'loyalty_points_earned': loyalty_points_earned,
        'product_count': sum(item['quantity'] for item in bag.values()),  # Number of products in the bag
    }

    print(f"Bag items in checkout: {context['bag_items']}")
    return render(request, 'checkout/checkout.html', context)
