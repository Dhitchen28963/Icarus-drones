from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render, redirect, reverse, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q
from django.db.models.functions import Lower, Substr
from custom_storages import MediaStorage
from products.constants import ATTACHMENTS
from .models import Product, Category
from .forms import ProductForm, ProductReviewForm
from profiles.models import Wishlist, UserProfile
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from decimal import Decimal, InvalidOperation
import json


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
    """Add a product to the store"""
    # Move categories outside if/else to make it available in all code paths
    categories = list(Category.objects.values_list('friendly_name', flat=True))

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)

        if form.is_valid():
            product = form.save(commit=False)

            if 'image' in request.FILES:
                image = request.FILES['image']

                try:
                    storage = MediaStorage()  # Use MediaStorage directly
                    file_name = storage.save(image.name, image)
                    product.image = file_name
                except Exception:
                    messages.error(
                        request,
                        "Error uploading image. Please try again."
                    )
                    return redirect('add_product')
            else:
                product.image = 'noimage.webp'

            try:
                product.save()
                messages.success(request, 'Successfully added product!')
                return redirect(reverse('product_detail', args=[product.id]))
            except Exception:
                messages.error(
                    request, "Error saving product. Please try again."
                )
        else:
            messages.error(
                request,
                'Failed to add product. Please ensure the form is valid.'
            )
    else:
        category_id = request.GET.get('category')
        initial_data = {'category': category_id} if category_id else {}
        form = ProductForm(initial=initial_data)

    context = {
        'form': form,
        'categories': categories,
    }
    return render(request, 'products/add_product.html', context)


@user_passes_test(is_staff_or_superuser)
@login_required
def edit_product(request, product_id):
    """Edit a product in the store"""
    product = get_object_or_404(Product, pk=product_id)
    old_image = product.image

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)

        if form.is_valid():
            if 'image' in request.FILES:
                # Upload new image to S3
                image = request.FILES['image']
                storage = MediaStorage()
                file_name = storage.save(image.name, image)
                product.image = file_name

                # Delete the old image
                if old_image and old_image != 'noimage.webp':
                    try:
                        storage.delete(old_image.name)
                    except Exception:
                        pass

            elif 'image-clear' in request.POST:
                # Clear the image
                if old_image and old_image != 'noimage.webp':
                    try:
                        storage = MediaStorage()
                        storage.delete(old_image.name)
                    except Exception:
                        pass
                product.image = 'noimage.webp'

            form.save()
            messages.success(request, 'Successfully updated product!')
            return redirect(reverse('product_detail', args=[product.id]))
        else:
            messages.error(
                request, 'Failed to update product. Please check the form.'
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

    def sanitize_value(value, spec):
        """Sanitize and normalize values for comparison."""
        if value in [None, "", "Not Available"]:
            return "Not Available"

        try:
            if spec == "Weight" and isinstance(value, str):
                return Decimal(
                    ''.join(
                        filter(
                            str.isdigit, value.lower().replace('g', '').strip()
                        )
                    )
                )
            elif spec in [
                "Flight Time", "Control Range", "Max Altitude", "Speed"
            ] and isinstance(value, str):
                return float(''.join(filter(str.isdigit, value)))
            elif isinstance(value, (int, float, Decimal)):
                return value
            else:
                # For string fields, return the value as-is
                return value
        except (ValueError, TypeError, InvalidOperation):
            return "Not Available"

    selected_drone = get_object_or_404(Product, pk=product_id)
    drones = Product.objects.filter(category__name="drones")
    compare_drone_id = request.GET.get('compare_drone')
    compare_drone = (
        get_object_or_404(Product, pk=compare_drone_id)
        if compare_drone_id
        else drones.first()
    )

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
        ('Weight', sanitize_value(selected_drone.weight, "Weight"),
         sanitize_value(compare_drone.weight, "Weight"), False),
        ('Rotors', selected_drone.rotors, compare_drone.rotors, True),
        ('GPS', selected_drone.gps, compare_drone.gps, True),
    ]

    specifications_with_colors = []
    for spec, left_value, right_value, better_is_higher in specifications:
        left_value = sanitize_value(left_value, spec)
        right_value = sanitize_value(right_value, spec)

        if left_value == "Not Available" or right_value == "Not Available":
            left_color = right_color = "text-muted"
        elif left_value == right_value:
            left_color = right_color = ""
        elif spec == "Weight" and isinstance(
            left_value, (int, float, Decimal)
        ):
            left_color = (
                "text-success" if left_value < right_value
                else "text-danger"
            )
            right_color = (
                "text-success" if right_value < left_value
                else "text-danger"
            )
        elif isinstance(left_value, (int, float, Decimal)) and isinstance(
            right_value, (int, float, Decimal)
        ):
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
        else:
            left_color = right_color = ""

        specifications_with_colors.append(
            (spec, left_value, left_color, right_value, right_color)
        )

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
