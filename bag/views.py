from decimal import Decimal 
from django.shortcuts import render, redirect, reverse, get_object_or_404
from django.http import HttpResponse
from django.contrib import messages
from products.constants import ATTACHMENTS
from products.models import Product

def get_attachment_name_by_sku(sku):
    """ Helper function to return the human-readable name of an attachment given its SKU """
    for attachment in ATTACHMENTS:
        if attachment['sku'] == sku:
            return attachment['name']
    return sku


def view_bag(request):
    """ A view that renders the bag contents page with loyalty points """
    bag = request.session.get('bag', {})
    total = Decimal(0)

    # Calculate total amount in the bag
    for item_id, item_data in bag.items():
        total += Decimal(item_data['price']) * item_data['quantity']

    # Calculate loyalty points (assuming 1 point per $10 spent)
    loyalty_points_earned = int(total // 10)

    context = {
        'bag': bag,
        'total': total,
        'loyalty_points_earned': loyalty_points_earned,
    }

    return render(request, 'bag/bag.html', context)


def add_to_bag(request, item_id):
    """ Add a quantity of the specified product to the shopping bag """
    quantity = int(request.POST.get('quantity'))
    redirect_url = request.POST.get('redirect_url')
    product = get_object_or_404(Product, pk=item_id)
    bag = request.session.get('bag', {})

    if str(item_id) in bag and isinstance(bag[str(item_id)], dict):
        bag[str(item_id)]['quantity'] += quantity
        messages.success(request, f'Updated {product.name} quantity to {bag[str(item_id)]["quantity"]}.')
    else:
        bag[str(item_id)] = {'quantity': quantity, 'price': float(product.price), 'sku': product.sku}
        messages.success(request, f'Added {product.name} to your bag.')

    request.session['bag'] = bag
    return redirect(redirect_url)


def add_custom_drone_to_bag(request):
    """Add a custom drone to the shopping bag"""
    if request.method == 'POST':
        sku = request.POST.get('sku')
        quantity = int(request.POST.get('quantity', 1))
        attachments = request.POST.getlist('attachments')

        try:
            product = Product.objects.get(sku=sku)
        except Product.DoesNotExist:
            messages.error(request, "The product you tried to add was not found.")
            return redirect('view_bag')

        # Create a unique key based on SKU and attachments
        custom_key = f"{sku}"
        if attachments:
            custom_key = f"{custom_key}-{'-'.join(attachments)}"

        bag = request.session.get('bag', {})

        # Calculate attachment costs and the final price
        extra_cost = sum(float(att['price']) for att in ATTACHMENTS if att['sku'] in attachments)
        final_price = float(product.price) + extra_cost  # Base price + attachment costs

        if custom_key in bag:
            bag[custom_key]['quantity'] += quantity
            attachment_names = [get_attachment_name_by_sku(att) for att in attachments]
            attachments_text = ', '.join(attachment_names)
            messages.success(request, f'Updated {product.name} with attachments: {attachments_text} quantity to {bag[custom_key]["quantity"]}.')
        else:
            bag[custom_key] = {
                'quantity': quantity,
                'price': final_price,
                'attachments': attachments,
                'sku': sku,
            }
            attachment_names = [get_attachment_name_by_sku(att) for att in attachments]
            attachments_text = ', '.join(attachment_names)
            if attachments:
                messages.success(request, f"{product.name} with attachments: {attachments_text} added to your bag.")
            else:
                messages.success(request, f"{product.name} without attachments added to your bag.")

        request.session['bag'] = bag
        return redirect('view_bag')


def adjust_bag(request, item_id):
    """Adjust the quantity of the specified product to the specified amount"""
    quantity = int(request.POST.get('quantity'))
    bag = request.session.get('bag', {})

    if str(item_id) in bag and isinstance(bag[str(item_id)], dict):
        if item_id.isdigit():
            product = get_object_or_404(Product, pk=item_id)
            if quantity > 0:
                bag[str(item_id)]['quantity'] = quantity
                messages.success(request, f'Updated {product.name} quantity to {quantity}.')
            else:
                bag.pop(str(item_id))
                messages.success(request, f'Removed {product.name} from your bag.')
        else:
            if quantity > 0:
                bag[item_id]['quantity'] = quantity
                messages.success(request, f'Updated {item_id} quantity to {quantity}.')
            else:
                bag.pop(item_id)
                messages.success(request, f'Removed {item_id} from your bag.')
    else:
        messages.error(request, "Error adjusting the bag. Item not found or is invalid.")

    request.session['bag'] = bag
    return redirect(reverse('view_bag'))


def remove_from_bag(request, item_id):
    """Remove the item from the shopping bag"""
    try:
        bag = request.session.get('bag', {})
        
        if item_id in bag:
            item_data = bag[item_id]
            sku = item_data.get('sku', item_id)
            attachments = item_data.get('attachments', [])

            if attachments:
                attachment_names = [get_attachment_name_by_sku(att) for att in attachments]
                formatted_attachments = ", ".join(attachment_names)
                message = f"Removed {sku} with attachments ({formatted_attachments}) from your bag."
            else:
                product = get_object_or_404(Product, sku=sku) if sku else None
                if product:
                    message = f"Removed {product.name} from your bag."
                else:
                    message = f"Removed {item_id} from your bag."

            bag.pop(item_id)
            messages.success(request, message)

        request.session['bag'] = bag
        return HttpResponse(status=200)

    except Exception as e:
        print(f"Error removing item: {e}")
        return HttpResponse(status=500)
