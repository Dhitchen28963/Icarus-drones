from django.shortcuts import render, redirect, get_object_or_404
from products.models import Product

def view_bag(request):
    """ A view that renders the bag contents page """
    return render(request, 'bag/bag.html')


def add_to_bag(request, item_id):
    """ Add a quantity of the specified product to the shopping bag """

    quantity = int(request.POST.get('quantity'))
    redirect_url = request.POST.get('redirect_url')
    bag = request.session.get('bag', {})

    if item_id in list(bag.keys()):
        bag[item_id] += quantity
    else:
        bag[item_id] = quantity

    request.session['bag'] = bag
    print(request.session['bag'])  # Debugging print statement to see the contents of the bag
    return redirect(redirect_url)


def add_custom_drone_to_bag(request):
    """ Add a custom drone to the shopping bag """
    # Get the SKU from the form
    sku = request.POST.get('sku')
    quantity = int(request.POST.get('quantity'))

    # Get any selected attachments
    attachments = request.POST.getlist('attachments')

    # Find the matching product based on the SKU
    product = get_object_or_404(Product, sku=sku)

    # Get the shopping bag from the session
    bag = request.session.get('bag', {})

    # Create a unique key for the custom drone in the bag (product ID + attachments)
    custom_key = f"{product.id}-{'-'.join(attachments)}" if attachments else str(product.id)

    # Calculate the additional cost for attachments
    extra_cost = 0
    if 'camera' in attachments:
        extra_cost += 299
    if 'vr-goggles' in attachments:
        extra_cost += 199
    if 'carry-case' in attachments:
        extra_cost += 49
    if 'extra-battery' in attachments:
        extra_cost += 99
    if 'extra-propellers' in attachments:
        extra_cost += 29
    if 'insurance' in attachments:
        extra_cost += 149

    # Calculate the final price by converting product.price (Decimal) to float
    final_price = float(product.price) + extra_cost

    # Add or update the custom drone in the bag
    if custom_key in bag:
        bag[custom_key]['quantity'] += quantity
    else:
        bag[custom_key] = {
            'quantity': quantity,
            'price': final_price,  # Storing as a float to avoid Decimal issues
            'attachments': attachments,
            'sku': sku,
        }

    # Save the updated bag to the session
    request.session['bag'] = bag

    # Debugging print statement to check the final contents of the bag
    print(f"Bag contents: {request.session['bag']}")

    # Redirect to the bag view
    return redirect('view_bag')