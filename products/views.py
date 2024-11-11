from django.conf import settings
from django.shortcuts import render, redirect, reverse, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from django.db.models.functions import Lower
from products.constants import ATTACHMENTS
from .models import Product, Category
from .forms import ProductForm

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

# View renders the custom_product.html template for customizing specific drones
def custom_product(request):
    """ A view to render the custom product page with customizable options """
    custom_drones = Product.objects.filter(category__name="custom_drones")
    product = custom_drones.first() if custom_drones.exists() else None

    drones = [
        {'name': 'Falcon X', 'value': 'falcon-x-10001'},
        {'name': 'Sky Hawk', 'value': 'sky-hawk-10002'},
        {'name': 'Phantom Vortex', 'value': 'phantom-vortex-10003'},
    ]

    colors = [
        ('black', 'Black'),
        ('white', 'White'),
        ('blue', 'Blue'),
        ('green', 'Green'),
        ('pink', 'Pink'),
        ('purple', 'Purple'),
        ('red', 'Red'),
        ('yellow', 'Yellow'),
        ('orange', 'Orange'),
    ]

    context = {
        'product': product,
        'drones': drones,
        'colors': colors,
        'ATTACHMENTS': ATTACHMENTS,
        'MEDIA_URL': settings.MEDIA_URL,
    }

    return render(request, 'products/custom_product.html', context)

def add_product(request):
    """ Add a product to the store """
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            messages.success(request, 'Successfully added product!')
            return redirect(reverse('product_detail', args=[product.id]))
        else:
            messages.error(request, 'Failed to add product. Please ensure the form is valid.')
    else:
        form = ProductForm()
        
    context = {
        'form': form,
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
    print("Product deleted message added to messages framework.")
    return redirect(reverse('products'))


def edit_custom_product(request, product_id):
    """ Edit a custom drone with proper toast messages """
    product = get_object_or_404(Product, pk=product_id)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f'Successfully updated {product.name}!')
            return redirect(reverse('edit_custom_product', args=[product.id]))
        else:
            messages.error(request, 'Failed to update the custom drone. Please ensure the form is valid.')
    else:
        form = ProductForm(instance=product)
        messages.info(request, f'You are editing {product.name}')

    # Extract type and color from SKU
    sku_parts = product.sku.split('-')
    product_type = sku_parts[0]
    product_color = sku_parts[-1]

    # Check if there are URL parameters for type and color
    if 'drone_type' in request.GET and 'drone_color' in request.GET:
        product_type = request.GET['drone_type']
        product_color = request.GET['drone_color']

    context = {
        'form': form,
        'product': product,
        'product_type': product_type,
        'product_color': product_color,
        'drones': [
            {'name': 'Falcon X', 'value': 'custom1'},
            {'name': 'Sky Hawk', 'value': 'custom2'},
            {'name': 'Phantom Vortex', 'value': 'custom3'},
        ],
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
    product_name = product.name  # Store the product name for the success message
    product.delete()
    messages.success(request, f'Custom drone "{product_name}" deleted successfully!')  # Include the product name in the message
    return redirect(reverse('products'))
