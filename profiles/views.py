from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import UserProfile, OrderIssue
from .forms import UserProfileForm, OrderIssueForm, OrderIssueResponseForm
from checkout.models import Order
from django.core.mail import send_mail
from .decorators import superuser_or_staff_required, superuser_required
from django.contrib.auth.models import User


@login_required
def profile(request):
    """ Display the user's profile. """
    profile = get_object_or_404(UserProfile, user=request.user)

    # Retrieve unresolved and resolved issues using `status`
    unresolved_issues = profile.user.order_issues.filter(status='in_progress')
    resolved_issues = profile.user.order_issues.filter(status='resolved')

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

    # Add `can_manage_issues` to the context
    can_manage_issues = (
        request.user.is_superuser or request.user.has_perm('profiles.can_manage_issues')
    )

    template = 'profiles/profile.html'
    context = {
        'form': form,
        'orders': orders,
        'unresolved_issues': unresolved_issues,
        'resolved_issues': resolved_issues,
        'on_profile_page': True,
        'can_manage_issues': can_manage_issues,
    }

    return render(request, template, context)


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
    # Retrieve the order via the user profile
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
    """ View to respond to a specific issue. """
    issue = get_object_or_404(OrderIssue, id=issue_id)

    if request.method == 'POST':
        form = OrderIssueResponseForm(request.POST, instance=issue)
        if form.is_valid():
            # Save the response and status directly from the form
            form.save()

            # Send email notification if the status is resolved
            if issue.status == 'resolved':
                send_mail(
                    subject=f"Response to your order issue: {issue.order.order_number}",
                    message=f"Dear {issue.user.username},\n\n{issue.response}\n\nBest regards,\nIcarus Drones Support Team",
                    from_email='support@icarusdrones.com',
                    recipient_list=[issue.user.email],
                )

            messages.success(request, 'Response saved and status updated.')
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
    """View to display messages for the user."""
    profile = request.user.userprofile
    unresolved_issues = profile.user.order_issues.filter(status='in_progress')
    resolved_issues = profile.user.order_issues.filter(status='resolved')

    context = {
        'unresolved_issues': unresolved_issues,
        'resolved_issues': resolved_issues,
    }
    return render(request, 'profiles/messages.html', context)


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