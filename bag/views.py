from django.shortcuts import render, redirect, reverse, get_object_or_404
from django.http import HttpResponse
from django.contrib import messages
from products.constants import ATTACHMENTS
from products.models import Product

def view_bag(request):
    """ A view that renders the bag contents page """
    return render(request, 'bag/bag.html')


def add_to_bag(request, item_id):
    """ Add a quantity of the specified product to the shopping bag """
    quantity = int(request.POST.get('quantity'))
    redirect_url = request.POST.get('redirect_url')
    product = get_object_or_404(Product, pk=item_id)  # Ensure correct lookup by ID, not SKU
    bag = request.session.get('bag', {})

    # Add to or update the bag
    if str(item_id) in bag:
        bag[str(item_id)]['quantity'] += quantity
    else:
        bag[str(item_id)] = {'quantity': quantity, 'price': float(product.price), 'sku': product.sku}
        messages.success(request, f'Added {product.name} to your bag')

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
        else:
            bag[custom_key] = {
                'quantity': quantity,
                'price': final_price,
                'attachments': attachments,
                'sku': sku,
            }

        request.session['bag'] = bag
        messages.success(request, f"{product.name} with attachments added to your bag.")
        return redirect('view_bag')


def adjust_bag(request, item_id):
    """Adjust the quantity of the specified product to the specified amount"""
    quantity = int(request.POST.get('quantity'))
    bag = request.session.get('bag', {})

    if quantity > 0:
        bag[str(item_id)] = quantity
    else:
        bag.pop(str(item_id))

    request.session['bag'] = bag
    return redirect(reverse('view_bag'))


def remove_from_bag(request, item_id):
    """Remove the item from the shopping bag"""
    try:
        bag = request.session.get('bag', {})
        
        if item_id in bag:
            bag.pop(item_id)

        request.session['bag'] = bag
        messages.success(request, f'Removed {item_id} from your bag')

        return HttpResponse(status=200)

    except Exception as e:
        print(f"Error removing item: {e}")
        return HttpResponse(status=500)