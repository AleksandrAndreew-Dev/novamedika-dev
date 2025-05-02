from django.core.paginator import Paginator
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
# Create your views here.
from django.shortcuts import render

from .forms import ProductSearchForm
from .models import Pharmacy, Product, Order
from .tasks import order_created

from django.db.models import Count
from django.core.cache import cache
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db.models import Q
from django.db.models import Func, Value



from elasticsearch import Elasticsearch
from elasticsearch_dsl import connections

# Подключение к Elasticsearch
es = Elasticsearch(hosts=["http://elasticsearch-node-1:9200"])

def index(request):
    query = request.GET.get('name', '').strip()  # Поиск по названию
    city = request.GET.get('city', '').strip()  # Поиск по городу
    form = ProductSearchForm(request.GET or None)

    # Кэширование списка городов
    unique_cities = cache.get('unique_cities')
    if not unique_cities:
        unique_cities = list(Pharmacy.objects.values_list('city', flat=True).distinct().order_by('city'))
        cache.set('unique_cities', unique_cities, 3600)  # Сохраняем в кэше на 1 час

    unique_cities = [{'city': c, 'is_selected': (c == city)} for c in unique_cities]

    # Оптимизация запросов к базе данных
    products = Product.objects.select_related('pharmacy')

    if query:
        # Используем Elasticsearch для поиска по названию
        body = {
            "query": {
                "bool": {
                    "must": [  # Обе части запроса должны быть выполнены
                        {
                            "multi_match": {
                                "query": query,  # Запрос, состоящий из двух слов
                                "fields": ["name"],  # Поле, в котором осуществляется поиск
                                "type": "bool_prefix",  # Использовать лучшее совпадение
                                "fuzziness": "AUTO",  # Автоматический уровень нечеткости
                                "operator": "and"  # Условие "и" для всех слов
                            }
                        }
                    ],

                }
            },
            "sort": [{"price": {"order": "asc"}}]
        }

        # Выполняем запрос в Elasticsearch
        response = es.search(index="products", body=body)

        # Получаем IDs продуктов из результатов Elasticsearch
        elastic_ids = [hit["_id"] for hit in response["hits"]["hits"]]

        # Фильтруем продукты в Django по ID
        products = products.filter(uuid__in=elastic_ids)

    if city:
        products = products.filter(pharmacy__city__iexact=city)  # Фильтр по городу

    # Группировка продуктов на уровне базы данных
    grouped_products = (
        products.values('name', 'pharmacy__city')
        .annotate(count=Count('uuid'))
        .order_by('name', 'pharmacy__city', 'price')
    )

    # Пагинация (10 записей на страницу)
    paginated_products = Paginator(grouped_products, 10)
    page_number = request.GET.get('page')
    page_obj = paginated_products.get_page(page_number)

    return render(request, 'pharmacies/index.html', {
        'form': form,
        'page_obj': page_obj,
        'unique_cities': unique_cities,
        'query': query,
        'city': city,
    })



def search_products(request):
    name_query = request.GET.get('name', '').strip()
    city_query = request.GET.get('city', '').strip()

    body = {
        "query": {
            "bool": {
                "must": [],
                "filter": []
            }
        }
    }

    if name_query:
        body["query"]["bool"]["must"].append({
            "multi_match": {
                "query": name_query,
                "fields": ["name"],
                "type": "bool_prefix",
                "fuzziness": "AUTO",
                "operator": "and"
            }
        })

    if city_query:
        body["query"]["bool"]["filter"].append({
            "match": {
                "pharmacy.city": city_query  # Фильтрация по точному совпадению
            }
        })

    body["_source"] = [
        'name',
        'form',
        'manufacturer',
        'country',
        'price',
        'quantity',
        'pharmacy.city',
        'pharmacy.name'
    ]

    try:
        response = es.search(index="products", body=body)
        print(f"Elasticsearch response: {response}")
    except Exception as e:
        print(f"Ошибка запроса к Elasticsearch: {e}")
        return render(request, 'pharmacies/error.html', {'message': 'Ошибка поиска'})

    grouped_products = {}
    for hit in response["hits"]["hits"]:
        product = hit["_source"]
        pharmacy_city = product.get("pharmacy", {}).get("city", "Unknown")
        pharmacy_name = product.get("pharmacy", {}).get("name", "Unknown")

        key = (product.get("name", "N/A"), product.get("form", "N/A"), product.get("manufacturer", "N/A"),
               product.get("country", "N/A"))
        if key not in grouped_products:
            grouped_products[key] = {
                "name": product.get("name", "N/A"),
                "form": product.get("form", "N/A"),
                "manufacturer": product.get("manufacturer", "N/A"),
                "country": product.get("country", "N/A"),
                "pharmacy_city": pharmacy_city,
                "pharmacy_name": pharmacy_name,
            }

    grouped_products_list = list(grouped_products.values())
    paginator = Paginator(grouped_products_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    unique_cities = Pharmacy.objects.values('city').distinct().order_by('city')
    for city_obj in unique_cities:
        city_obj['is_selected'] = (city_obj['city'] == city_query)

    return render(request, 'pharmacies/search_products_results.html', {
        'grouped_products': page_obj,
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
            name__iexact=name,
            form__iexact=form,
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
    products = Product.objects.select_related('pharmacy').all().order_by('price')

    if query:
        search_vector = SearchVector('name', config='russian')
        search_query = SearchQuery(query, config='russian')
        products = products.annotate(search=search_vector).filter(
            Q(search=search_query) | Q(name__icontains=query)
        )
    #
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

    first_product = grouped_products_list[0] if grouped_products_list else None

    # Render the search results template
    return render(request, 'pharmacies/search_with_results.html', {
        'page_obj': page_obj,
        'unique_cities': unique_cities,
        'unique_forms': unique_forms,
        'query': query,
        'city': city,
        'form_query': form_query,
        'first_product': first_product,
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
        product_form = request.POST.get('product_form')
        product_price = request.POST.get('productPrice')
        pharmacy_name = request.POST.get('pharmacyName')
        pharmacy_number = request.POST.get('pharmacyNumber')
        order = Order.objects.create(user_name=user_name, user_surname=user_surname,
                                     user_phone=user_phone, quantity=quantity,
                                     product_name=product_name,
                                     product_form=product_form,
                                     product_price=product_price,
                                     pharmacy_name=pharmacy_name,
                                     pharmacy_number=pharmacy_number)
        order.save()
        order_created.delay(str(order.uuid))

        return HttpResponse("Ваш заказ отправлен! Ожидайте подтверждение от аптеки")

    return HttpResponse("Неверный запрос.")


