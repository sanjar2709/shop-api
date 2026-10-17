import pytest

from apps.common.tests.factories import ProductFactory

pytestmark = pytest.mark.django_db


def test_cart_requires_auth(api_client):
    assert api_client.get('/api/v1/cart/').status_code == 401


def test_empty_cart_is_created_on_first_request(user_client):
    response = user_client.get('/api/v1/cart/')

    assert response.status_code == 200
    assert response.data['items'] == []
    assert response.data['total_price'] == '0.00'


def test_add_item(user_client, product):
    response = user_client.post('/api/v1/cart/items/', {'product': product.slug, 'quantity': 2})

    assert response.status_code == 201
    assert response.data['items'][0]['quantity'] == 2
    assert response.data['total_price'] == '200.00'


def test_adding_same_product_increases_quantity(user_client, product):
    user_client.post('/api/v1/cart/items/', {'product': product.slug, 'quantity': 1})
    response = user_client.post('/api/v1/cart/items/', {'product': product.slug, 'quantity': 2})

    assert len(response.data['items']) == 1
    assert response.data['items'][0]['quantity'] == 3


def test_cannot_add_more_than_in_stock(user_client, product):
    user_client.post('/api/v1/cart/items/', {'product': product.slug, 'quantity': 4})
    response = user_client.post('/api/v1/cart/items/', {'product': product.slug, 'quantity': 2})

    assert response.status_code == 400
    assert 'quantity' in response.data


def test_cannot_add_inactive_product(user_client):
    product = ProductFactory(is_active=False)

    response = user_client.post('/api/v1/cart/items/', {'product': product.slug})

    assert response.status_code == 400


def test_update_and_remove_item(user_client, product):
    item_id = user_client.post('/api/v1/cart/items/', {'product': product.slug}).data['items'][0]['id']

    response = user_client.patch(f'/api/v1/cart/items/{item_id}/', {'quantity': 5})
    assert response.data['total_price'] == '500.00'

    assert user_client.patch(f'/api/v1/cart/items/{item_id}/', {'quantity': 6}).status_code == 400

    assert user_client.delete(f'/api/v1/cart/items/{item_id}/').status_code == 204
    assert user_client.get('/api/v1/cart/').data['items'] == []


def test_cannot_touch_other_users_cart_item(user_client, staff_client, product):
    item_id = staff_client.post('/api/v1/cart/items/', {'product': product.slug}).data['items'][0]['id']

    assert user_client.delete(f'/api/v1/cart/items/{item_id}/').status_code == 404
