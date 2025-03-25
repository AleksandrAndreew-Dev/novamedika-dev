from django.core.paginator import Paginator
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
# Create your views here.
from django.shortcuts import render

from .forms import ProductSearchForm
from .models import Pharmacy, Product, Order
from .tasks import order_created

def search_products(request):
    name_query = request.GET.get('name', '').strip()
    city_query = request.GET.get('city', '').strip()

    # If both fields are empty, return an empty result set
    if not name_query and not city_query:
        return render(request, 'pharmacies/search_products_results.html', {
            'grouped_products': [],  # No results
            'unique_cities': Pharmacy.objects.values('city').distinct().order_by('city'),
            'query': name_query,
            'city_query': city_query
        })

    # Start with all products and apply filters dynamically
    products = Product.objects.select_related('pharmacy').all()

    if name_query:
        products = products.filter(name__icontains=name_query)  # Filter by name
    if city_query:
        products = products.filter(pharmacy__city__icontains=city_query)  # Filter by city

    # Group products by name, form, and pharmacy, while summing quantities
   # Extract unique forms for products
    unique_forms = {}
    for product in products:
        key = (product.name, product.form)  # Unique key for name and form
        if key not in unique_forms:
            unique_forms[key] = {
                'name': product.name,
                'form': product.form
            }
    # Convert unique forms to a list
    unique_forms_list = list(unique_forms.values())


    # Convert grouped products to a list for pagination


    # Fetch unique cities for the dropdown
    unique_cities = Pharmacy.objects.values('city').distinct().order_by('city')
    for city in unique_cities:
        city['is_selected'] = (city['city'] == city_query)  # Ensure the selected city is marked

    # Pass grouped data to the template
    return render(request, 'pharmacies/search_products_results.html', {
        'grouped_products': unique_forms_list,
        'unique_cities': unique_cities,
        'query': name_query,
        'city_query': city_query,
    })


def search_pharmacies(request):
    name = request.GET.get('name', '').strip()  # Get the selected product name
    form = request.GET.get('form', '').strip()  # Get the selected product form
    city = request.GET.get('city', '').strip()  # Get the selected city

    pharmacies = []
    if name and form:
        # Filter products by name, form, and pharmacy city
        pharmacies = Product.objects.filter(
            name__icontains=name,
            form__icontains=form,
            pharmacy__city__exact=city  # Add city filtering
        ).select_related('pharmacy')

    return render(request, 'pharmacies/search_pharmacies.html', {
        'pharmacies': pharmacies,
        'selected_name': name,
        'selected_form': form,
        'selected_city': city,
    })

def search(request):
    query = request.GET.get('name', '').strip()  # Search query for product name
    city = request.GET.get('city', '').strip()  # Filter by city
    form_query = request.GET.get('form', '').strip()  # Filter by form

    # Filter products dynamically based on user input
    products = Product.objects.select_related('pharmacy').all()  # Optimize with select_related

    if query:
        products = products.filter(name__icontains=query)
    if form_query:
        products = products.filter(form__iexact=form_query)
    if city and city != 'Все города':  # Skip filtering if "Все города" is selected
        products = products.filter(pharmacy__city__iexact=city)

    # Group products by name, form, pharmacy name, city, and pharmacy number while summing quantities
    grouped_products = {}
    for product in products:
        key = (
            product.name,
            product.form,
            product.pharmacy.name if product.pharmacy else 'Unknown',
            product.pharmacy.city if product.pharmacy else 'Unknown',
            product.pharmacy.pharmacy_number if product.pharmacy else 'N/A'  # Include pharmacy number in key
        )
        if key not in grouped_products:
            grouped_products[key] = {
                'name': product.name,
                'form': product.form,
                'pharmacy_name': product.pharmacy.name if product.pharmacy else 'Unknown',
                'pharmacy_city': product.pharmacy.city if product.pharmacy else 'Unknown',
                'pharmacy_address': product.pharmacy.address if product.pharmacy else 'Unknown',
                'pharmacy_phone': product.pharmacy.phone if product.pharmacy else 'Unknown',
                'pharmacy_number': product.pharmacy.pharmacy_number if product.pharmacy else 'N/A',
                'price': product.price,
                'quantity': product.quantity,
                'manufacturer': product.manufacturer,
                'country': product.country,
                'pharmacies': []  # Initialize pharmacies list
            }
        else:
            # Sum the quantities for the same product and pharmacy
            grouped_products[key]['quantity'] += product.quantity

        # Add pharmacy details to the pharmacies list
        grouped_products[key]['pharmacies'].append({
            'pharmacy_name': product.pharmacy.name,
            'pharmacy_number': product.pharmacy.pharmacy_number,
            'pharmacy_city': product.pharmacy.city,
            'pharmacy_address': product.pharmacy.address,
            'pharmacy_phone': product.pharmacy.phone,
        })

    # Convert grouped products to a list for pagination
    grouped_products_list = list(grouped_products.values())
    paginator = Paginator(grouped_products_list, 20)  # Paginate 20 items per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Fetch unique cities for the dropdown
    unique_cities = Pharmacy.objects.values('city').distinct().order_by('city')
    for city_obj in unique_cities:
        city_obj['is_selected'] = (city_obj['city'] == city)

    # Fetch unique forms for filtering
    unique_forms = Product.objects.values('form').distinct().order_by('form')
    for form_obj in unique_forms:
        form_obj['is_selected'] = (form_obj['form'] == form_query)

    # Render the search results template
    return render(request, 'pharmacies/search_with_results.html', {
        'page_obj': page_obj,
        'unique_cities': unique_cities,
        'unique_forms': unique_forms,
        'query': query,
        'city': city,
        'form_query': form_query,
    })


def index(request):
    query = request.GET.get('name', '').strip()  # Search query for product name
    city = request.GET.get('city', '').strip()  # Search query for city
    form = ProductSearchForm(request.GET or None)

    # Filter products by name and city only
    products = Product.objects.all()
    if query:
        products = products.filter(name__icontains=query)  # Filter by name
    if city:
        products = products.filter(pharmacy__city__icontains=city)  # Filter by city

    # Group products by name and city
    grouped_products = {}
    for product in products:
        key = (product.name, product.pharmacy.city)  # Group by name and city
        if key not in grouped_products:
            grouped_products[key] = {
                'name': product.name,
                'city': product.pharmacy.city,
                'count': 1  # Count products grouped by name and city
            }
        else:
            grouped_products[key]['count'] += 1

    # Paginate grouped products (10 products per page)
    paginated_products = Paginator(list(grouped_products.values()), 10)
    page_number = request.GET.get('page')
    page_obj = paginated_products.get_page(page_number)

    # Fetch unique cities for filtering
    unique_cities = Pharmacy.objects.values('city').distinct().order_by('city')
    for city_obj in unique_cities:
        city_obj['is_selected'] = (city_obj['city'] == city)

    return render(request, 'pharmacies/index.html', {
        'form': form,
        'page_obj': page_obj,
        'unique_cities': unique_cities,
        'query': query,
        'city': city,
    })



def pharmacy_list(request):
    pharmacies = Pharmacy.objects.all()
    return render(request, 'pharmacies/pharmacy/list.html',
                  {'pharmacies': pharmacies})


def pharmacy_detail(request, pharmacy_name, pharmacy_number):
    try:
        pharmacy = get_object_or_404(Pharmacy, name=pharmacy_name,
                                     pharmacy_number=pharmacy_number,
                                     )
    except Pharmacy.DoesNotExist:
        raise Http404('Pharmacy not found')
    return render(request, 'pharmacies/pharmacy/detail.html', {'pharmacy': pharmacy})


def reserve(request):
    if request.method == "POST":
        user_name = request.POST.get('userName')
        user_surname = request.POST.get('userSurname')
        user_phone = request.POST.get('userPhone')
        quantity = request.POST.get('quantity')
        product_name = request.POST.get('productName')
        product_price = request.POST.get('productPrice')
        pharmacy_name = request.POST.get('pharmacyName')
        pharmacy_number = request.POST.get('pharmacyNumber')
        order = Order.objects.create(user_name=user_name, user_surname=user_surname,
                                     user_phone=user_phone, quantity=quantity,
                                     product_name=product_name,
                                     product_price=product_price,
                                     pharmacy_name=pharmacy_name,
                                     pharmacy_number=pharmacy_number)
        order.save()
        order_created.delay(order.id)

        return HttpResponse("Ваш заказ отправлен! Ожидайте подтверждение от аптеки")

    return HttpResponse("Неверный запрос.")
