from django.conf import settings
from django.shortcuts import render, redirect, reverse, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from django.db.models.functions import Lower, Substr
from products.constants import ATTACHMENTS
from .models import Product, Category, Attachment
from .forms import ProductForm, AttachmentForm

# View to show all products, including sorting and search queries
def all_products(request):
    """ A view to show all products, including sorting and search queries """
    products = Product.objects.all()
    query = None
    categories = None
    sort = None
    direction = None

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
                messages.error(request, "You didn't enter any search criteria!")
                return redirect(reverse('products'))

            queries = Q(name__icontains=query) | Q(description__icontains=query)
            products = products.filter(queries)

    current_sorting = f'{sort}_{direction}'

    context = {
        'products': products,
        'search_term': query,
        'current_categories': categories,
        'current_sorting': current_sorting,
    }

    return render(request, 'products/products.html', context)

# View to show individual product details
def product_detail(request, product_id):
    """ A view to show individual product details """
    product = get_object_or_404(Product, pk=product_id)

    context = {
        'product': product,
    }

    return render(request, 'products/product_detail.html', context)

# View renders the custom drones
def custom_product(request):
    """ A view to render the custom product page with customizable options """

    # Fetch all products categorized as 'Custom Drones'
    custom_drones = Product.objects.filter(category__name="custom_drones").annotate(
        base_model=Substr('sku', 1, 15)
    )

    unique_drones = {}
    for drone in custom_drones:
        base_model = drone.base_model

        # Ensure that all trailing digits and hyphens are removed from the base model
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
            messages.error(request, 'Failed to add product. Please ensure the form is valid.')
    else:
        category_id = request.GET.get('category')
        initial_data = {'category': category_id} if category_id else {}
        form = ProductForm(initial=initial_data)

        # Pass category-friendly names to JavaScript
        categories = list(Category.objects.values_list('friendly_name', flat=True))
        
    context = {
        'form': form,
        'categories': categories,
    }
    return render(request, 'products/add_product.html', context)

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
            messages.error(request, 'Failed to update product. Please ensure the form is valid.')
    else:
        form = ProductForm(instance=product)
        messages.info(request, f'You are editing {product.name}')

    context = {
        'form': form,
        'product': product,
    }

    return render(request, 'products/edit_product.html', context)

def delete_product(request, product_id):
    """ Delete a product from the store """
    product = get_object_or_404(Product, pk=product_id)
    product.delete()
    messages.success(request, 'Product deleted!')
    return redirect(reverse('products'))


def edit_custom_product(request, product_id):
    """ Edit a custom drone with attachment management functionality """
    product = get_object_or_404(Product, pk=product_id)
    form = ProductForm(instance=product)
    attachment_form = AttachmentForm(request.POST or None, request.FILES or None)

    if request.method == 'POST':
        if 'update_product' in request.POST:
            form = ProductForm(request.POST, request.FILES, instance=product)
            if form.is_valid():
                form.save()
                messages.success(request, f'Successfully updated {product.name}!')
                return redirect(f"{reverse('edit_custom_product', args=[product.id])}?drone_type={product.sku.split('-')[0].lower()}&drone_color={product.sku.split('-')[-1].lower()}&show_toast=true")
            else:
                messages.error(request, 'Failed to update the custom drone. Please ensure the form is valid.')

        elif 'add_attachment' in request.POST and attachment_form.is_valid():
            new_attachment = attachment_form.save(commit=False)
            new_attachment.product = product
            new_attachment.save()
            messages.success(request, 'New attachment added successfully!')
            return redirect(f"{reverse('edit_custom_product', args=[product.id])}?drone_type={product.sku.split('-')[0].lower()}&drone_color={product.sku.split('-')[-1].lower()}&show_toast=true")

        elif 'remove_attachments' in request.POST:
            removed_attachments = request.POST.getlist('remove_attachments')
            for attachment_id in removed_attachments:
                attachment = get_object_or_404(Attachment, id=attachment_id)
                attachment.delete()
                messages.success(request, f'Attachment "{attachment.name}" removed successfully!')
            return redirect(f"{reverse('edit_custom_product', args=[product.id])}?drone_type={product.sku.split('-')[0].lower()}&drone_color={product.sku.split('-')[-1].lower()}&show_toast=true")

    else:
        form = ProductForm(instance=product)
        messages.info(request, f'You are editing {product.name}')

    # Handle SKU extraction and prioritize URL parameters for setting drone type and color
    sku_parts = product.sku.split('-') if product.sku else ['unknown']
    product_type = request.GET.get('drone_type', sku_parts[0]).lower()
    product_color = request.GET.get('drone_color', sku_parts[-1]).lower()

    # Map each drone to a full identifier for consistency with product_type
    custom_drones = Product.objects.filter(category__name="custom_drones").values('name', 'sku')
    unique_drones = []
    seen_drones = set()
    for drone in custom_drones:
        # Ensure 'name' and 'sku' are not None to avoid AttributeError
        if drone['name'] and drone['sku']:
            drone_name_parts = drone['name'].split(' ')
            if len(drone_name_parts) > 1:
                # Create a consistent format like "phantom-vortex"
                drone_base_model = f"{drone_name_parts[0].lower()}-{drone_name_parts[1].lower()}"
            else:
                drone_base_model = drone['sku'].split('-')[0].lower()
        elif drone['sku']:
            drone_base_model = drone['sku'].split('-')[0].lower()
        else:
            drone_base_model = 'unknown'

        if drone_base_model not in seen_drones:
            seen_drones.add(drone_base_model)
            unique_drones.append({
                'name': drone['name'].split(' - ')[0] if drone['name'] else 'Unnamed Drone',
                'value': drone_base_model
            })

    # Filter attachments to exclude any that are marked as removed in the session
    filtered_attachments = [att for att in ATTACHMENTS if att["id"] not in request.session.get('removed_attachments', [])]
    available_attachments = [att for att in ATTACHMENTS if att["id"] not in [a["id"] for a in filtered_attachments]]

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


def delete_custom_product(request, product_id):
    """ Delete a custom drone and redirect to the products page """
    product = get_object_or_404(Product, pk=product_id)
    product_name = product.name
    product.delete()
    messages.success(request, f'Custom drone "{product_name}" deleted successfully!')
    return redirect(reverse('products'))
