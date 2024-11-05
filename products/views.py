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
            if 'drones' in categories:
                categories += ['deals', 'new_arrivals', 'bundles']
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
    # Define the three specific drone models with SKU format
    drones = [
        {'name': 'Falcon X', 'value': 'falcon-x-10001'},
        {'name': 'Sky Hawk', 'value': 'sky-hawk-10002'},
        {'name': 'Phantom Vortex', 'value': 'phantom-vortex-10003'},
    ]

    # Available color options
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
            form.save()
            messages.success(request, 'Successfully added product!')
            return redirect(reverse('add_product'))
        else:
            messages.error(request, 'Failed to add product. Please ensure the form is valid.')
    else:
        form = ProductForm()
        
    template = 'products/add_product.html'
    context = {
        'form': form,
    }

    return render(request, template, context)


from django.shortcuts import render, get_object_or_404, redirect, reverse
from django.contrib import messages
from .models import Product
from .forms import ProductForm

def edit_product(request, product_id):
    """ Edit a product in the store """
    product = get_object_or_404(Product, pk=product_id)
    
    # Check if the product is a customizable drone
    is_custom_drone = product.category.name == "Customizable Drones"  # Adjust as per your custom drone category/identifier

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

    template = 'products/edit_product.html'
    context = {
        'form': form,
        'product': product,
        'is_custom_drone': is_custom_drone,
    }

    return render(request, template, context)
