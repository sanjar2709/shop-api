import pytest

from apps.common.tests.factories import CategoryFactory, ProductFactory

pytestmark = pytest.mark.django_db


def test_anyone_can_list_products(api_client, product):
    response = api_client.get('/api/v1/products/')

    assert response.status_code == 200
    assert response.data['count'] == 1


def test_customer_cannot_create_product(user_client, category):
    data = {'title': 'Phone', 'slug': 'phone', 'category': category.slug, 'price': '10.00'}

    assert user_client.post('/api/v1/products/', data).status_code == 403


def test_staff_can_create_product(staff_client, category):
    data = {'title': 'Phone', 'slug': 'phone', 'category': category.slug, 'price': '10.00', 'stock': 3}

    response = staff_client.post('/api/v1/products/', data)

    assert response.status_code == 201
    assert response.data['in_stock'] is True


def test_negative_price_is_rejected(staff_client, category):
    data = {'title': 'Phone', 'slug': 'phone', 'category': category.slug, 'price': '-1.00'}

    assert staff_client.post('/api/v1/products/', data).status_code == 400


def test_inactive_products_are_hidden_from_customers(api_client, staff_client):
    ProductFactory(is_active=False)
    ProductFactory(category=CategoryFactory(is_active=False))
    ProductFactory()

    assert api_client.get('/api/v1/products/').data['count'] == 1
    assert staff_client.get('/api/v1/products/').data['count'] == 3


@pytest.mark.parametrize(('query', 'expected'), (
    ('?min_price=50', ['Expensive']),
    ('?max_price=50', ['Cheap', 'Sold out']),
    ('?in_stock=true', ['Expensive', 'Cheap']),
    ('?in_stock=false', ['Sold out']),
    ('?search=sold', ['Sold out']),
))
def test_product_filters(api_client, query, expected):
    ProductFactory(title='Expensive', price='100.00', stock=1)
    ProductFactory(title='Cheap', price='10.00', stock=1)
    ProductFactory(title='Sold out', price='20.00', stock=0)

    response = api_client.get(f'/api/v1/products/{query}')

    assert sorted(p['title'] for p in response.data['results']) == sorted(expected)


def test_filter_by_category(api_client):
    phones = CategoryFactory(slug='phones')
    ProductFactory(category=phones)
    ProductFactory()

    response = api_client.get('/api/v1/products/?category=phones')

    assert response.data['count'] == 1


def test_ordering_by_price(api_client):
    for price in ('30.00', '10.00', '20.00'):
        ProductFactory(price=price)

    response = api_client.get('/api/v1/products/?ordering=price')

    assert [p['price'] for p in response.data['results']] == ['10.00', '20.00', '30.00']
