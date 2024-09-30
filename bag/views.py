from django.shortcuts import render, redirect, reverse, get_object_or_404
from django.http import HttpResponse
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
    return redirect(redirect_url)


def add_custom_drone_to_bag(request):
    """ Add a custom drone to the shopping bag """
    sku = request.POST.get('sku')
    quantity = int(request.POST.get('quantity'))

    attachments = request.POST.getlist('attachments')
    product = get_object_or_404(Product, sku=sku)
    bag = request.session.get('bag', {})

    custom_key = f"{product.id}-{'-'.join(attachments)}" if attachments else str(product.id)

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

    final_price = float(product.price) + extra_cost

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
    return redirect('view_bag')


def adjust_bag(request, item_id):
    """Adjust the quantity of the specified product to the specified amount"""

    quantity = int(request.POST.get('quantity'))
    bag = request.session.get('bag', {})

    if quantity > 0:
        bag[item_id] = quantity
    else:
        bag.pop(item_id)

    request.session['bag'] = bag
    return redirect(reverse('view_bag'))


def remove_from_bag(request, item_id):
    """Remove the item from the shopping bag"""

    try:
        bag = request.session.get('bag', {})

        # Remove the item directly without checking for sizes
        bag.pop(item_id)

        request.session['bag'] = bag
        return HttpResponse(status=200)

    except Exception as e:
        return HttpResponse(status=500)
