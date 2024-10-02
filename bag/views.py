from django.shortcuts import render, redirect, reverse, get_object_or_404
from django.http import HttpResponse
from django.contrib import messages
from products.constants import ATTACHMENTS
from products.models import Product

def view_bag(request):
    """ A view that renders the bag contents page """
    messages.info(request, "Viewing your bag")
    return render(request, 'bag/bag.html')


def add_to_bag(request, item_id):
    """ Add a quantity of the specified product to the shopping bag """
    quantity = int(request.POST.get('quantity'))
    redirect_url = request.POST.get('redirect_url')
    product = get_object_or_404(Product, pk=item_id)
    bag = request.session.get('bag', {})

    # Ensure that the item is always stored as a dictionary with 'quantity', 'price', and 'sku'
    if str(item_id) in bag and isinstance(bag[str(item_id)], dict):
        bag[str(item_id)]['quantity'] += quantity
        messages.success(request, f'Updated {product.name} quantity to {bag[str(item_id)]["quantity"]}.')
    else:
        # Add the product as a dictionary to the bag
        bag[str(item_id)] = {'quantity': quantity, 'price': float(product.price), 'sku': product.sku}
        messages.success(request, f'Added {product.name} to your bag.')

    request.session['bag'] = bag
    return redirect(redirect_url)



def add_custom_drone_to_bag(request):
    """Add a custom drone to the shopping bag"""
    if request.method == 'POST':
        sku = request.POST.get('sku')  # The SKU should include the color
        quantity = int(request.POST.get('quantity', 1))
        attachments = request.POST.getlist('attachments')

        # Fetch the product using SKU
        try:
            product = Product.objects.get(sku=sku)
        except Product.DoesNotExist:
            messages.error(request, "The product you tried to add was not found.")
            return redirect('view_bag')

        # Create a unique key based on SKU and attachments
        custom_key = f"{sku}"
        if attachments:
            custom_key = f"{custom_key}-{'-'.join(attachments)}"

        # Get the bag from session
        bag = request.session.get('bag', {})

        # Calculate attachment costs and the final price
        extra_cost = sum(float(att['price']) for att in ATTACHMENTS if att['sku'] in attachments)
        final_price = float(product.price) + extra_cost  # Base price + attachment costs

        # Add or update the custom drone in the bag
        if custom_key in bag:
            bag[custom_key]['quantity'] += quantity
            messages.success(request, f'Updated {product.name} quantity to {bag[custom_key]["quantity"]}.')
        else:
            bag[custom_key] = {
                'quantity': quantity,
                'price': final_price,
                'attachments': attachments,
                'sku': sku,
            }
            if attachments:
                messages.success(request, f"{product.name} with attachments added to your bag.")
            else:
                messages.success(request, f"{product.name} without attachments added to your bag.")

        request.session['bag'] = bag
        return redirect('view_bag')


from django.shortcuts import get_object_or_404
from products.models import Product

def adjust_bag(request, item_id):
    """Adjust the quantity of the specified product to the specified amount"""
    quantity = int(request.POST.get('quantity'))
    bag = request.session.get('bag', {})

    # Check if the item is in the bag and it's a dictionary (to ensure it's not an integer)
    if str(item_id) in bag and isinstance(bag[str(item_id)], dict):
        # Check if it's a regular product with an ID
        if item_id.isdigit():
            product = get_object_or_404(Product, pk=item_id)  # Fetch product by ID
            if quantity > 0:
                bag[str(item_id)]['quantity'] = quantity
                # Use the SKU to match the message format of custom drones
                messages.success(request, f'Updated {product.sku} quantity to {quantity}.')
            else:
                bag.pop(str(item_id))
                messages.success(request, f'Removed {product.sku} from your bag.')
        else:
            # Handle custom drones with SKU and attachments
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
            # Retrieve item data
            item_data = bag[item_id]
            sku = item_data.get('sku', item_id)
            attachments = item_data.get('attachments', [])

            # Check if the item has attachments (for custom drones)
            if attachments:
                # Get a friendly list of attachment names
                attachment_names = [att['name'] for att in ATTACHMENTS if att['sku'] in attachments]
                formatted_attachments = ", ".join(attachment_names)
                message = f"Removed {sku} with attachments ({formatted_attachments}) from your bag."
            else:
                # For regular products or custom drones without attachments
                product = get_object_or_404(Product, sku=sku) if sku else None
                if product:
                    message = f"Removed {product.name} from your bag."
                else:
                    message = f"Removed {item_id} from your bag."  # fallback in case the product can't be found
            
            # Remove the item from the bag
            bag.pop(item_id)

            # Display the friendly message for both custom drones and regular products
            messages.success(request, message)

        request.session['bag'] = bag
        return HttpResponse(status=200)

    except Exception as e:
        print(f"Error removing item: {e}")
        return HttpResponse(status=500)

