from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render, redirect, reverse, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q
from django.db.models.functions import Lower, Substr
from products.constants import ATTACHMENTS
from .models import Product, Category, Attachment, ProductReview
from .forms import ProductForm, AttachmentForm, ProductReviewForm
from profiles.models import Wishlist, UserProfile
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import json
from decimal import Decimal


# Helper function to check if the user is a staff member or superuser
def is_staff_or_superuser(user):
    return user.is_superuser or user.is_staff


# View to show all products, including sorting and search queries
def all_products(request):
    """ A view to show all products, including sorting and search queries """
    products = Product.objects.all()
    query = None
    categories = None
    sort = None
    direction = None
    per_page = request.GET.get('per_page', '20')

    if request.GET:
        if 'sort' in request.GET:
            sortkey = request.GET['sort']
            sort = sortkey
            if sortkey == 'name':
                sortkey = 'lower_name'
                products = products.annotate(lower_name=Lower('name'))
            if sortkey == 'category':
                sortkey = 'category__name'

            if 'direction' in request.GET:
                direction = request.GET['direction']
                if direction == 'desc':
                    sortkey = f'-{sortkey}'
            products = products.order_by(sortkey)

        if 'category' in request.GET:
            categories = request.GET['category'].split(',')
            products = products.filter(category__name__in=categories)
            categories = Category.objects.filter(name__in=categories)

        if 'q' in request.GET:
            query = request.GET['q']
            if not query:
                messages.error(
                    request,
                    "You didn't enter any search criteria!"
                )
                return redirect(reverse('products'))

            queries = (
                Q(name__icontains=query) |
                Q(description__icontains=query)
            )
            products = products.filter(queries)

    # Ensure default ordering for consistent pagination
    products = products.order_by('id')

    # Get the user's wishlist if authenticated
    wishlist_products = []
    if request.user.is_authenticated:
        wishlist_products = (
            request.user.userprofile.wishlist.products
            .values_list('id', flat=True)
        )

    # Pagination logic
    if per_page != 'all':
        try:
            per_page = int(per_page)
        except ValueError:
            per_page = 20
        paginator = Paginator(products, per_page)
        page = request.GET.get('page')
        try:
            products = paginator.page(page)
        except PageNotAnInteger:
            products = paginator.page(1)
        except EmptyPage:
            products = paginator.page(paginator.num_pages)
    current_sorting = f'{sort}_{direction}'

    context = {
        'products': products,
        'search_term': query,
        'current_categories': categories,
        'current_sorting': current_sorting,
        'wishlist_products': wishlist_products,
    }

    return render(request, 'products/products.html', context)


def product_detail(request, product_id):
    """ View to show individual product details with filtering """
    product = get_object_or_404(Product, pk=product_id)

    # Check if the product is in the user's wishlist
    is_in_wishlist = (
        request.user.is_authenticated and
        request.user.userprofile.wishlist.products.filter(
            pk=product.pk
        ).exists()
    )

    # Get filter for reviews based on stars
    star_filter = request.GET.get('stars')
    reviews = product.reviews.all()

    # Ensure consistent ordering for pagination
    reviews = reviews.order_by('-created_at')

    # Handle specific star filter, excluding 'all'
    if star_filter and star_filter != 'all':
        reviews = reviews.filter(rating=star_filter)

    # Paginate reviews
    paginator = Paginator(reviews, 5)
    page = request.GET.get('page')

    try:
        reviews = paginator.page(page)
    except PageNotAnInteger:
        reviews = paginator.page(1)
    except EmptyPage:
        reviews = paginator.page(paginator.num_pages)

    context = {
        'product': product,
        'reviews': reviews,
        'star_filter': star_filter,
        'is_in_wishlist': is_in_wishlist,
        'range': range(1, 6),
    }

    return render(request, 'products/product_detail.html', context)


def custom_product(request):
    """ A view to render the custom product page with customizable options """

    # Fetch all products categorized as 'Custom Drones'
    custom_drones = Product.objects.filter(
        category__name="custom_drones"
    ).annotate(base_model=Substr('sku', 1, 15))

    unique_drones = {}
    for drone in custom_drones:
        base_model = drone.base_model

        # Ensure all trailing digits and hyphens are removed
        if base_model:
            base_model = base_model.rstrip("0123456789-")

            # Store unique drone models only once by their cleaned base name
            if base_model not in unique_drones:
                unique_drones[base_model] = {
                    'name': drone.name.split(' - ')[0],
                    'value': base_model,
                    'colors': [],
                }

            # Add color options for each drone type
            unique_drones[base_model]['colors'].append({
                'color': drone.color,
                'image': drone.image,
            })

    drone_options = list(unique_drones.values())

    colors = [
        ('black', 'Black'), ('white', 'White'), ('blue', 'Blue'),
        ('green', 'Green'), ('pink', 'Pink'), ('purple', 'Purple'),
        ('red', 'Red'), ('yellow', 'Yellow'), ('orange', 'Orange'),
    ]

    context = {
        'product': custom_drones.first() if custom_drones.exists() else None,
        'drones': drone_options,
        'colors': colors,
        'ATTACHMENTS': ATTACHMENTS,
        'MEDIA_URL': settings.MEDIA_URL,
    }

    return render(request, 'products/custom_product.html', context)


@user_passes_test(is_staff_or_superuser)
@login_required
def add_product(request):
    """ Add a product to the store with category-specific field handling """
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            if not product.image:
                product.image = 'products/noimage.webp'
            product.save()
            messages.success(request, 'Successfully added product!')
            return redirect(reverse('product_detail', args=[product.id]))
        else:
            messages.error(
                request,
                'Failed to add product. Please ensure the form is valid.'
            )
    else:
        category_id = request.GET.get('category')
        initial_data = {'category': category_id} if category_id else {}
        form = ProductForm(initial=initial_data)

        # Pass category-friendly names
        categories = list(Category.objects.values_list(
            'friendly_name', flat=True))

    context = {
        'form': form,
        'categories': categories,
    }
    return render(request, 'products/add_product.html', context)


@user_passes_test(is_staff_or_superuser)
@login_required
def edit_product(request, product_id):
    """ Edit a product in the store """
    product = get_object_or_404(Product, pk=product_id)

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Successfully updated product!')
            return redirect(reverse('product_detail', args=[product.id]))
        else:
            messages.error(
                request,
                'Failed to update product. Please ensure the form is valid.'
            )
    else:
        form = ProductForm(instance=product)
        messages.info(request, f'You are editing {product.name}')

    context = {
        'form': form,
        'product': product,
    }

    return render(request, 'products/edit_product.html', context)


@user_passes_test(is_staff_or_superuser)
@login_required
def delete_product(request, product_id):
    """ Delete a product from the store """
    product = get_object_or_404(Product, pk=product_id)
    product.delete()
    messages.success(request, 'Product deleted!')
    return redirect(reverse('products'))


@user_passes_test(is_staff_or_superuser)
@login_required
def edit_custom_product(request, product_id):
    """ Edit a custom drone with attachment management functionality """
    product = get_object_or_404(Product, pk=product_id)
    form = ProductForm(instance=product)
    attachment_form = AttachmentForm(
        request.POST or None,
        request.FILES or None
    )

    if request.method == 'POST':
        if 'update_product' in request.POST:
            form = ProductForm(request.POST, request.FILES, instance=product)
            if form.is_valid():
                form.save()
                messages.success(
                    request,
                    f'Successfully updated {product.name}!'
                )
                return redirect(
                    f"{reverse('edit_custom_product', args=[product.id])}?"
                    f"drone_type={product.sku.split('-')[0].lower()}&"
                    f"drone_color={product.sku.split('-')[-1].lower()}&"
                    f"show_toast=true"
                )
            else:
                messages.error(
                    request,
                    'Failed to update custom drone, ensure the form is valid.'
                )

        elif 'add_attachment' in request.POST and attachment_form.is_valid():
            new_attachment = attachment_form.save(commit=False)
            new_attachment.product = product
            new_attachment.save()
            messages.success(request, 'New attachment added successfully!')
            return redirect(
                f"{reverse('edit_custom_product', args=[product.id])}?"
                f"drone_type={product.sku.split('-')[0].lower()}&"
                f"drone_color={product.sku.split('-')[-1].lower()}&"
                f"show_toast=true"
            )

        elif 'remove_attachments' in request.POST:
            removed_attachments = request.POST.getlist('remove_attachments')
            for attachment_id in removed_attachments:
                attachment = get_object_or_404(Attachment, id=attachment_id)
                attachment.delete()
                messages.success(
                    request,
                    f'Attachment "{attachment.name}" removed successfully!'
                )
            return redirect(
                f"{reverse('edit_custom_product', args=[product.id])}?"
                f"drone_type={product.sku.split('-')[0].lower()}&"
                f"drone_color={product.sku.split('-')[-1].lower()}&"
                f"show_toast=true"
            )

    else:
        form = ProductForm(instance=product)
        messages.info(request, f'You are editing {product.name}')

    # Handle SKU extraction and prioritize URL parameters
    sku_parts = product.sku.split('-') if product.sku else ['unknown']
    product_type = request.GET.get('drone_type', sku_parts[0]).lower()
    product_color = request.GET.get('drone_color', sku_parts[-1]).lower()

    # Map each drone to a full identifier for consistency with product_type
    custom_drones = Product.objects.filter(
        category__name="custom_drones").values('name', 'sku')
    unique_drones = []
    seen_drones = set()
    for drone in custom_drones:
        # Ensure 'name' and 'sku' are not None to avoid AttributeError
        if drone['name'] and drone['sku']:
            drone_name_parts = drone['name'].split(' ')
            if len(drone_name_parts) > 1:
                # Create a consistent format
                drone_base_model = (
                    f"{drone_name_parts[0].lower()}-"
                    f"{drone_name_parts[1].lower()}"
                )
            else:
                drone_base_model = drone['sku'].split('-')[0].lower()
        elif drone['sku']:
            drone_base_model = drone['sku'].split('-')[0].lower()
        else:
            drone_base_model = 'unknown'

        if drone_base_model not in seen_drones:
            seen_drones.add(drone_base_model)
            unique_drones.append({
                'name': drone['name'].split(' - ')[0] if drone['name']
                else 'Unnamed Drone',
                'value': drone_base_model
            })

    # Filter attachments to exclude removed ones
    removed_attachments = request.session.get('removed_attachments', [])
    filtered_attachments = [
        att for att in ATTACHMENTS if att["id"] not in removed_attachments]
    available_attachments = [
        att for att in ATTACHMENTS
        if att["id"] not in [a["id"] for a in filtered_attachments]]

    context = {
        'form': form,
        'product': product,
        'attachment_form': attachment_form,
        'attachments': filtered_attachments,
        'available_attachments': available_attachments,
        'product_type': product_type,
        'product_color': product_color,
        'drones': unique_drones,
        'colors': [
            ('black', 'Black'),
            ('white', 'White'),
            ('blue', 'Blue'),
            ('green', 'Green'),
            ('pink', 'Pink'),
            ('purple', 'Purple'),
            ('red', 'Red'),
            ('yellow', 'Yellow'),
            ('orange', 'Orange'),
        ],
    }

    return render(request, 'products/edit_custom_drone.html', context)


@user_passes_test(is_staff_or_superuser)
@login_required
def delete_custom_product(request, product_id):
    """ Delete a custom drone and redirect to the products page """
    product = get_object_or_404(Product, pk=product_id)
    product_name = product.name
    product.delete()
    messages.success(
        request,
        f'Custom drone "{product_name}" deleted successfully!'
    )
    return redirect(reverse('products'))


def compare_products(request, product_id):
    """
    View to compare a selected drone against others.
    """
    def sanitize_weight(value):
        if value:
            return Decimal(value.lower().replace('g', '').strip())
        return Decimal('0')

    selected_drone = get_object_or_404(Product, pk=product_id)
    drones = Product.objects.filter(category__name="drones")
    compare_drone_id = request.GET.get('compare_drone')
    compare_drone = get_object_or_404(
        Product, pk=compare_drone_id) if compare_drone_id else drones.first()

    specifications = [
        ('Price', selected_drone.price, compare_drone.price, False),
        ('Flight Time', selected_drone.flight_time,
         compare_drone.flight_time, True),
        ('Control Range', selected_drone.control_range,
         compare_drone.control_range, True),
        ('Max Altitude', selected_drone.max_altitude,
         compare_drone.max_altitude, True),
        ('Speed', selected_drone.speed, compare_drone.speed, True),
        ('Camera', selected_drone.camera, compare_drone.camera, True),
        ('Camera Quality', selected_drone.camera_quality,
         compare_drone.camera_quality, True),
        ('Collision Avoidance', selected_drone.collision_avoidance,
         compare_drone.collision_avoidance, True),
        ('Wind Resistance', selected_drone.wind_resistance,
         compare_drone.wind_resistance, True),
        ('Weight', sanitize_weight(selected_drone.weight),
         sanitize_weight(compare_drone.weight), False),
        ('Rotors', selected_drone.rotors, compare_drone.rotors, True),
        ('GPS', selected_drone.gps, compare_drone.gps, True),
    ]

    specifications_with_colors = []
    for spec, left_value, right_value, better_is_higher in specifications:
        if left_value == right_value:
            left_color = right_color = ""
        elif spec == "Weight":
            left_color = (
                "text-success" if left_value < right_value
                else "text-danger"
            )
            right_color = (
                "text-success" if right_value < left_value
                else "text-danger"
            )
        else:
            left_color = (
                "text-success"
                if (better_is_higher and left_value > right_value)
                or (not better_is_higher and left_value < right_value)
                else "text-danger"
            )
            right_color = (
                "text-success"
                if (better_is_higher and right_value > left_value)
                or (not better_is_higher and right_value < left_value)
                else "text-danger"
            )

        specifications_with_colors.append(
            (spec, left_value, left_color, right_value, right_color))

    context = {
        'selected_drone': selected_drone,
        'compare_drone': compare_drone,
        'drones': drones,
        'specifications': specifications_with_colors,
    }

    return render(request, 'products/compare_products.html', context)


@login_required
def add_product_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        form = ProductReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.product = product
            review.save()
            messages.success(
                request, 'Your review has been submitted successfully!')
            return redirect('product_detail', product_id=product_id)
        else:
            messages.error(
                request,
                'There was an error with your review submission. '
                'Please ensure all fields are filled out.'
            )
    else:
        form = ProductReviewForm()

    return render(request, 'products/product_detail.html', {
        'product': product,
        'form': form,
    })


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
                return JsonResponse(
                    {'error': 'Product ID missing'}, status=400)

            product = get_object_or_404(Product, id=product_id)
            user_profile = get_object_or_404(UserProfile, user=request.user)

            wishlist, created = Wishlist.objects.get_or_create(
                user_profile=user_profile)

            if product in wishlist.products.all():
                wishlist.products.remove(product)
                return JsonResponse(
                    {
                        'status': 'removed',
                        'message': (
                            f'Removed "{product.name}" '
                            f'from your wishlist!'
                        )
                    }
                )
            else:
                wishlist.products.add(product)
                return JsonResponse(
                    {'status': 'added',
                     'message': f'Added "{product.name}" to your wishlist!'})

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse(
                {'error': f'Error occurred: {e}'}, status=500)

    return JsonResponse({'error': 'Invalid request'}, status=400)
