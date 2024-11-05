from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from .models import UserProfile
from .forms import UserProfileForm
from checkout.models import Order

def profile(request):
    """ Display the user's profile. """
    profile = get_object_or_404(UserProfile, user=request.user)

    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully')
        else:
            messages.error(request, 'Update failed. Please ensure the form is valid.')
    else:
        form = UserProfileForm(instance=profile)
    
    # Retrieve orders and calculate loyalty points for each
    orders = profile.orders.all()
    for order in orders:
        order.loyalty_points_earned = int(order.grand_total // 10)

    template = 'profiles/profile.html'
    context = {
        'form': form,
        'orders': orders,
        'on_profile_page': True,
    }

    return render(request, template, context)

def order_history(request, order_number):
    """ Display the order history for a specific order. """
    order = get_object_or_404(Order, order_number=order_number)

    # Calculate loyalty points earned for this specific order
    loyalty_points_earned = int(order.grand_total // 10)  # Assuming 1 point per $10 spent

    messages.info(request, (
        f'This is a past confirmation for order number {order_number}. '
        'A confirmation email was sent on the order date.'
    ))

    template = 'checkout/checkout_success.html'
    context = {
        'order': order,
        'from_profile': True,
        'loyalty_points_earned': loyalty_points_earned,
    }

    return render(request, template, context)
