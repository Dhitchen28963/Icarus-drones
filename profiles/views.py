from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import UserProfile, OrderIssue, Wishlist, UserMessage, RepairRequest, ContactMessage
from .forms import UserProfileForm, OrderIssueForm, OrderIssueResponseForm, RepairRequestResponseForm, ContactMessageResponseForm
from checkout.models import Order
from products.models import Product
from django.core.mail import send_mail
from .decorators import superuser_or_staff_required, superuser_required
from utils.mailchimp_utils import Mailchimp
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponse
import json, re


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

            # Sync with Mailchimp
            try:
                mailchimp = Mailchimp()
                mailchimp.subscribe_user(
                    email=request.user.email,
                    first_name=request.user.first_name,
                    last_name=request.user.last_name,
                    tags=["Profile Updated"]
                )
            except Exception:
                pass
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
    """View to list all order issues, repair requests, and contact messages."""
    # Filter issues, repair requests, and contact messages based on status
    issues = OrderIssue.objects.filter(status='in_progress')
    resolved_issues = OrderIssue.objects.filter(status='resolved')
    unresolved_repair_requests = RepairRequest.objects.filter(status='in_progress')
    resolved_repair_requests = RepairRequest.objects.filter(status='resolved')
    unresolved_contact_messages = ContactMessage.objects.filter(status='in_progress')
    resolved_contact_messages = ContactMessage.objects.filter(status='resolved')

    # Combine all unresolved and resolved items
    unresolved_items = list(issues) + list(unresolved_repair_requests) + list(unresolved_contact_messages)
    resolved_items = list(resolved_issues) + list(resolved_repair_requests) + list(resolved_contact_messages)

    context = {
        'issues': issues,
        'resolved_issues': resolved_issues,
        'repair_requests': unresolved_repair_requests,
        'resolved_repair_requests': resolved_repair_requests,
        'contact_messages': unresolved_contact_messages,
        'resolved_contact_messages': resolved_contact_messages,
        'unresolved_items': unresolved_items,
        'resolved_items': resolved_items,
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

            parent_message = UserMessage.objects.filter(
                user=issue.user,
                created_by=issue.user,
                content__icontains=issue.description,
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
        # Show all messages for superusers or staff
        parent_messages = UserMessage.objects.filter(parent_message__isnull=True).order_by('-created_at')
        unresolved_issues = OrderIssue.objects.filter(status='in_progress')
        resolved_issues = OrderIssue.objects.filter(status='resolved')
        repair_requests = RepairRequest.objects.all().order_by('-created_at')
        contact_messages = ContactMessage.objects.all().order_by('-created_at')
    else:
        profile = request.user.userprofile
        parent_messages = UserMessage.objects.filter(
            user=request.user, parent_message__isnull=True
        ).order_by('-created_at')
        unresolved_issues = profile.user.order_issues.filter(status='in_progress')
        resolved_issues = profile.user.order_issues.filter(status='resolved')
        repair_requests = RepairRequest.objects.filter(user=request.user).order_by('-created_at')
        contact_messages = ContactMessage.objects.filter(email=request.user.email).order_by('-created_at')

    # Attach the original report to each parent message
    for message in parent_messages:
        try:
            # Use regex to extract the order number
            match = re.search(r'\b[0-9A-F]{32}\b', message.content)
            if match:
                order_number = match.group(0)

                # Find the corresponding OrderIssue
                message.order_issue = OrderIssue.objects.filter(
                    order__order_number=order_number,
                    user=message.user
                ).first()

                # Attach the initial report
                if message.order_issue:
                    message.initial_report = UserMessage(
                        created_by=message.order_issue.user,
                        content=message.order_issue.description,
                        created_at=message.order_issue.created_at,
                    )
        except Exception:
            pass

    context = {
        'parent_messages': parent_messages,
        'unresolved_issues': unresolved_issues,
        'resolved_issues': resolved_issues,
        'repair_requests': repair_requests,
        'contact_messages': contact_messages,
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


@login_required
def manage_messages(request):
    """View to display and manage repair requests and contact messages."""
    repair_requests = RepairRequest.objects.all().order_by('-created_at')
    contact_messages = ContactMessage.objects.all().order_by('-created_at')

    context = {
        'repair_requests': repair_requests,
        'contact_messages': contact_messages,
        'unresolved_issues': [],
        'resolved_issues': [],
        'parent_messages': [],
    }
    return render(request, 'profiles/manage_messages.html', context)



@login_required
def handle_contact_submission(request):
    """Handle Contact Us form submissions."""
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')

        if not name or not email or not message:
            messages.error(request, "Please fill out all fields.")
            return redirect('contact_us')

        ContactMessage.objects.create(
            user=request.user,
            name=name,
            email=email,
            message=message,
        )
        messages.success(request, 'Thank you for contacting us! We will get back to you soon.')
        return redirect('contact_us')

    return render(request, 'profiles/contact_us.html')



@login_required
def handle_repair_submission(request):
    """Handle Repair Request form submissions."""
    if request.method == 'POST':
        drone_model = request.POST.get('drone_model')
        issue_description = request.POST.get('issue_description')
        email = request.POST.get('email')

        if not drone_model or not issue_description or not email:
            messages.error(request, "Please fill out all required fields.")
            return redirect('drone_repair')

        RepairRequest.objects.create(
            drone_model=drone_model,
            issue_description=issue_description,
            email=email,
            user=request.user if request.user.is_authenticated else None,
        )
        messages.success(request, 'Your repair request has been submitted.')
        return redirect('drone_repair')

    # Render the Repair Request form for GET requests
    return render(request, 'profiles/drone_repair.html')


@superuser_or_staff_required
def respond_to_repair_request(request, request_id):
    repair_request = get_object_or_404(RepairRequest, id=request_id)
    messages_history = UserMessage.objects.filter(repair_request=repair_request).order_by('created_at')

    if request.method == 'POST':
        form = RepairRequestResponseForm(request.POST, instance=repair_request)
        if form.is_valid():
            # Save status update
            repair_request.status = form.cleaned_data['status']
            repair_request.save()

            # Create message
            response_message = form.cleaned_data['response']
            UserMessage.objects.create(
                repair_request=repair_request,
                user=repair_request.user,
                created_by=request.user,
                content=response_message,
            )

            # Determine how to address the recipient
            user_info = f"Dear {repair_request.user.username}," if repair_request.user else "Dear Customer,"

            # Send email notification
            send_mail(
                subject="Repair Request Update",
                message=(
                    f"{user_info}\n\n"
                    f"We have reviewed your repair request:\n\n"
                    f"\"{repair_request.issue_description}\"\n\n"
                    f"Our response:\n\n"
                    f"\"{response_message}\"\n\n"
                    f"Best regards,\nIcarus Drones Support Team"
                ),
                from_email='support@icarusdrones.com',
                recipient_list=[repair_request.email],
            )
            messages.success(request, 'Response sent successfully.')
            return redirect('manage_issues')
        else:
            messages.error(request, 'Failed to send response. Please check the form.')
    else:
        form = RepairRequestResponseForm(instance=repair_request)

    return render(request, 'profiles/repair_response.html', {
        'form': form, 
        'repair_request': repair_request,
        'messages_history': messages_history,
    })


@superuser_or_staff_required
def respond_to_contact_message(request, message_id):
    contact_message = get_object_or_404(ContactMessage, id=message_id)
    messages_history = UserMessage.objects.filter(contact_message=contact_message).order_by('created_at')

    if request.method == 'POST':
        form = ContactMessageResponseForm(request.POST, instance=contact_message)
        if form.is_valid():
            # Save status update
            contact_message.status = form.cleaned_data['status']
            contact_message.save()

            # Create message
            response_message = form.cleaned_data['response']
            UserMessage.objects.create(
                user=contact_message.user,
                created_by=request.user,
                content=response_message,
                contact_message=contact_message
            )

            # Send email notification
            send_mail(
                subject="Response to your inquiry",
                message=(
                    f"Dear {contact_message.name},\n\n"
                    f"We have reviewed your inquiry:\n\n"
                    f"\"{contact_message.message}\"\n\n"
                    f"Our response:\n\n"
                    f"\"{response_message}\"\n\n"
                    f"Best regards,\nIcarus Drones Support Team"
                ),
                from_email='support@icarusdrones.com',
                recipient_list=[contact_message.email],
            )
            messages.success(request, 'Response sent successfully.')
            return redirect('manage_issues')
        else:
            messages.error(request, 'Failed to send response. Please check the form.')
    else:
        form = ContactMessageResponseForm(instance=contact_message)

    return render(request, 'profiles/contact_response.html', {
        'form': form,
        'message': contact_message,
        'messages_history': messages_history,
    })
