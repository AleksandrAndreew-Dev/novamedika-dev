from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView
from django.http import Http404, HttpResponse
# Create your views here.
from django.shortcuts import render
from .forms import ProductSearchForm, ReserveForm
from .models import Pharmacy, Product, Order
from django.core.paginator import Paginator
from .tasks import order_created






def index(request):
    query = request.GET.get('q', '')
    city = request.GET.get('city', '')
    form_query = request.GET.get('form', '')
    form = ProductSearchForm(request.GET or None)

    products = []
    if query or city or form_query:
        if form.is_valid():
            query = form.cleaned_data.get('q', '')

        products = Product.objects.all()
        if form_query:
            products = products.filter(category=form_query)
        if city:
            products = products.filter(pharmacy__city=city)
        if query:
            products = products.filter(name__icontains=query)

    grouped_products = {}
    for product in products:
        key = (product.pharmacy, product.name)
        if key not in grouped_products:
            grouped_products[key] = {
                'product': product,
                'count': 1
            }
        else:
            grouped_products[key]['count'] += 1

    grouped_forms = Product.objects.values('category').distinct().order_by('category')

    paginated_products = Paginator(list(grouped_products.values()), 10)  # 10 продуктов на страницу
    page_number = request.GET.get('page')
    page_obj = paginated_products.get_page(page_number)
    pharmacies = Pharmacy.objects.all()
    unique_cities = Pharmacy.objects.values('city').distinct().order_by('city')
    for city in unique_cities:
        city['is_selected'] = (city['city'] == request.GET.get('city', ''))

    return render(request, 'pharmacies/index.html', {
        'form': form,
        'page_obj': page_obj,
        'pharmacies': pharmacies,
        'unique_cities': unique_cities,
        'grouped_forms': grouped_forms,
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


def product_search(request):
    query = request.GET.get('q', '')
    city = request.GET.get('city', '')
    form_query = request.GET.get('form', '')
    form = ProductSearchForm(request.GET or None)

    products = []
    if query or city or form_query:
        if form.is_valid():
            query = form.cleaned_data.get('q', '')

        products = Product.objects.all()
        if form_query:
            products = products.filter(category=form_query)
        if city:
            products = products.filter(pharmacy__city=city)
        if query:
            products = products.filter(name__icontains=query)

    grouped_products = {}
    for product in products:
        key = (product.pharmacy, product.name)
        if key not in grouped_products:
            grouped_products[key] = {
                'product': product,
                'count': 1
            }
        else:
            grouped_products[key]['count'] += 1

    grouped_forms = Product.objects.values('category').distinct().order_by('category')

    paginated_products = Paginator(list(grouped_products.values()), 10)  # 10 продуктов на страницу
    page_number = request.GET.get('page')
    page_obj = paginated_products.get_page(page_number)
    pharmacies = Pharmacy.objects.all()
    unique_cities = Pharmacy.objects.values('city').distinct().order_by('city')

    return render(request, 'pharmacies/search.html', {
        'form': form,
        'page_obj': page_obj,
        'pharmacies': pharmacies,
        'unique_cities': unique_cities,
        'grouped_forms': grouped_forms,
    })



def product_search_with_results(request):
    query = request.GET.get('q', '')
    city = request.GET.get('city', '')
    form_query = request.GET.get('form', '')
    form = ProductSearchForm(request.GET or None)

    products = []
    if query or city or form_query:
        if form.is_valid():
            query = form.cleaned_data.get('q', '')

        products = Product.objects.all()
        if form_query:
            products = products.filter(category=form_query)
        if city:
            products = products.filter(pharmacy__city=city)
        if query:
            products = products.filter(name__icontains=query)
        products = products.order_by('price')

    grouped_products = {}
    for product in products:
        key = (product.pharmacy, product.name)
        if key not in grouped_products:
            grouped_products[key] = {
                'product': product,
                'count': 1
            }
        else:
            grouped_products[key]['count'] += 1

    grouped_forms = Product.objects.values('category').distinct().order_by('category')

    paginated_products = Paginator(list(grouped_products.values()), 20)  # 10 продуктов на страницу
    page_number = request.GET.get('page')
    page_obj = paginated_products.get_page(page_number)
    pharmacies = Pharmacy.objects.all()
    unique_cities = Pharmacy.objects.values('city').distinct().order_by('city')
    for city in unique_cities:
        city['is_selected'] = (city['city'] == request.GET.get('city', ''))

    return render(request, 'pharmacies/search_with_results.html', {
        'form': form,
        'page_obj': page_obj,
        'pharmacies': pharmacies,
        'unique_cities': unique_cities,
        'grouped_forms': grouped_forms,
        'selected_product': None,
    })


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


        # Логика бронирования
        # print(f"Бронирование: {product_name}, ожидаемая цена: {product_price} в {pharmacy_name}"
        #       f" №{pharmacy_number} для {user_name} {user_surname}. Телефон: {user_phone}, Количество: {quantity}")

        return HttpResponse("Ваш заказ отправлен! Ожидайте подтверждение от аптеки")

    return HttpResponse("Неверный запрос.")


