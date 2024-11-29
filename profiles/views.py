from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import UserProfile, OrderIssue, Wishlist, UserMessage
from .forms import UserProfileForm, OrderIssueForm, OrderIssueResponseForm
from checkout.models import Order
from products.models import Product
from django.core.mail import send_mail
from .decorators import superuser_or_staff_required, superuser_required
from django.contrib.auth.models import User
from django.http import JsonResponse
import json


@login_required
def profile(request):
    """ Display the user's profile. """
    profile = get_object_or_404(UserProfile, user=request.user)

    # Retrieve unresolved and resolved issues using `status`
    unresolved_issues = profile.user.order_issues.filter(status='in_progress')
    resolved_issues = profile.user.order_issues.filter(status='resolved')

    # Retrieve wishlist for preview
    wishlist_products = profile.wishlist.products.all()

    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully')
        else:
            messages.error(request, 'Update failed. Please ensure the form is valid.')
    else:
        form = UserProfileForm(instance=profile)

    # Retrieve orders without recalculating loyalty points
    orders = profile.orders.all()

    template = 'profiles/profile.html'
    context = {
        'form': form,
        'orders': orders,
        'wishlist_products': wishlist_products,
        'unresolved_issues': unresolved_issues,
        'resolved_issues': resolved_issues,
        'on_profile_page': True,
    }

    return render(request, template, context)


@login_required
def wishlist_view(request):
    """View to display the user's wishlist."""
    user_profile = get_object_or_404(UserProfile, user=request.user)
    wishlist, created = Wishlist.objects.get_or_create(user_profile=user_profile)
    wishlist_products = wishlist.products.all()
    return render(request, 'profiles/wishlist.html', {'wishlist_products': wishlist_products})


def order_history(request, order_number):
    """ Display the order history for a specific order. """
    order = get_object_or_404(Order, order_number=order_number)

    messages.info(request, (
        f'This is a past confirmation for order number {order_number}. '
        'A confirmation email was sent on the order date.'
    ))

    template = 'checkout/checkout_success.html'
    context = {
        'order': order,
        'from_profile': True,
        'loyalty_points_earned': order.loyalty_points,
    }

    return render(request, template, context)


@login_required
def report_order_issue(request, order_number):
    """Allow users to report an issue with an order."""
    order = get_object_or_404(
        Order,
        order_number=order_number,
        user_profile__user=request.user
    )

    if request.method == 'POST':
        form = OrderIssueForm(request.POST)
        if form.is_valid():
            issue = form.save(commit=False)
            issue.user = request.user
            issue.order = order
            issue.status = 'in_progress'
            issue.save()

            # Notify admin/support via email
            send_mail(
                subject=f"Order Issue Reported: {order_number}",
                message=f"User {request.user.username} reported an issue with order {order_number}.\n\n"
                        f"Issue Type: {issue.get_issue_type_display()}\n"
                        f"Description: {issue.description}",
                from_email='support@icarusdrones.com',
                recipient_list=['admin@icarusdrones.com'],
            )

            messages.success(request, 'Your issue has been reported. We will contact you shortly.')
            return redirect('order_history', order_number=order_number)
        else:
            messages.error(request, 'There was an error with your submission. Please check the form.')
    else:
        form = OrderIssueForm()

    return render(request, 'profiles/report_issue.html', {'form': form, 'order': order})


@superuser_or_staff_required
def manage_issues(request):
    """ View to list all order issues. """
    issues = OrderIssue.objects.filter(status='in_progress')
    resolved_issues = OrderIssue.objects.filter(status='resolved')

    context = {
        'issues': issues,
        'resolved_issues': resolved_issues,
    }
    return render(request, 'profiles/manage_issues.html', context)


@superuser_or_staff_required
def respond_to_issue(request, issue_id):
    """View to respond to a specific issue."""
    issue = get_object_or_404(OrderIssue, id=issue_id)

    if request.method == 'POST':
        form = OrderIssueResponseForm(request.POST, instance=issue)
        if form.is_valid():
            form.save()

            # Get the most recent message related to this issue, if any
            parent_message = UserMessage.objects.filter(
                user=issue.user,
                created_by=issue.user,
                content__icontains=issue.description,  # Match the issue description
            ).order_by('-created_at').first()

            # Add the response to the user's message trail
            UserMessage.objects.create(
                user=issue.user,
                created_by=request.user,
                content=f"Response to your issue for order {issue.order.order_number}: {issue.response}",
                parent_message=parent_message,
            )

            # Send email notification if the issue is resolved
            if issue.status == 'resolved':
                send_mail(
                    subject=f"Response to your order issue: {issue.order.order_number}",
                    message=f"Dear {issue.user.username},\n\n{issue.response}\n\nBest regards,\nIcarus Drones Support Team",
                    from_email='support@icarusdrones.com',
                    recipient_list=[issue.user.email],
                )

            messages.success(request, 'Response saved and message sent to the customer.')
            return redirect('manage_issues')
        else:
            messages.error(request, 'There was an error saving your response. Please try again.')
    else:
        form = OrderIssueResponseForm(instance=issue)

    context = {
        'form': form,
        'issue': issue,
    }
    return render(request, 'profiles/respond_to_issue.html', context)



@login_required
def messages_view(request):
    """View to display messages for the user or all messages for superusers/staff."""
    if request.user.is_superuser or request.user.is_staff:
        # Show all parent messages for superusers or staff
        parent_messages = UserMessage.objects.filter(parent_message__isnull=True).order_by('-created_at')
        unresolved_issues = OrderIssue.objects.filter(status='in_progress')
        resolved_issues = OrderIssue.objects.filter(status='resolved')
    else:
        # Show only messages for the current user
        profile = request.user.userprofile
        parent_messages = UserMessage.objects.filter(
            user=request.user, parent_message__isnull=True
        ).order_by('-created_at')

        unresolved_issues = profile.user.order_issues.filter(status='in_progress')
        resolved_issues = profile.user.order_issues.filter(status='resolved')

    context = {
        'parent_messages': parent_messages,
        'unresolved_issues': unresolved_issues,
        'resolved_issues': resolved_issues,
    }
    return render(request, 'profiles/messages.html', context)



@login_required
def respond_to_message(request, message_id):
    """Handle responses to messages."""
    if request.method == "POST":
        original_message = get_object_or_404(UserMessage, id=message_id)

        response_content = request.POST.get("response")
        if response_content:
            # Create a response message linked to the original sender
            UserMessage.objects.create(
                user=original_message.created_by,
                created_by=request.user,
                content=response_content,
                parent_message=original_message
            )
            messages.success(request, "Your response has been sent successfully.")
        else:
            messages.error(request, "Your response cannot be empty.")

        return redirect("messages")


@superuser_required
def manage_staff(request):
    if not request.user.is_superuser:
        return redirect('home')

    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')
        user = User.objects.get(id=user_id)

        if action == 'make_staff':
            user.is_staff = True
            user.save()
            messages.success(request, f"{user.username} is now a staff member.")
        elif action == 'remove_staff':
            user.is_staff = False
            user.save()
            messages.success(request, f"{user.username} is no longer a staff member.")

        return redirect('manage_staff')

    users = User.objects.all()
    return render(request, 'profiles/manage_staff.html', {'users': users})


@login_required
def toggle_wishlist(request):
    """
    Toggle a product in the user's wishlist.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            if not product_id:
                return JsonResponse({'error': 'Product ID missing'}, status=400)

            product = get_object_or_404(Product, id=product_id)
            user_profile = get_object_or_404(UserProfile, user=request.user)

            wishlist, created = Wishlist.objects.get_or_create(user_profile=user_profile)

            if product in wishlist.products.all():
                wishlist.products.remove(product)
                return JsonResponse({'status': 'removed', 'message': f'Removed "{product.name}" from your wishlist!'})
            else:
                wishlist.products.add(product)
                return JsonResponse({'status': 'added', 'message': f'Added "{product.name}" to your wishlist!'})

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': f'Error occurred: {e}'}, status=500)

    return JsonResponse({'error': 'Invalid request'}, status=400)