import threading
from datetime import timedelta

import pytest
from django.core import mail
from django.db import connection
from django.utils import timezone
from rest_framework.test import APIClient

from apps.common.tests.factories import CartItemFactory, ProductFactory, UserFactory
from apps.orders.models import Order
from apps.orders.services import create_order
from apps.orders.tasks import cancel_unpaid_orders

ADDRESS = {'shipping_address': 'Tashkent, Chilonzor 1', 'phone': '+998901234567'}


@pytest.fixture
def cart_item(user, product):
    return CartItemFactory(cart__user=user, product=product, quantity=2)


@pytest.mark.django_db
class TestCreateOrder:
    def test_empty_cart(self, user_client):
        response = user_client.post('/api/v1/orders/', ADDRESS)

        assert response.status_code == 400
        assert 'cart' in response.data

    def test_order_is_created_from_cart(self, user_client, user, product, cart_item):
        response = user_client.post('/api/v1/orders/', ADDRESS)

        assert response.status_code == 201
        assert response.data['status'] == 'pending'
        assert response.data['total_price'] == '200.00'
        assert response.data['items'][0]['product_title'] == product.title

        product.refresh_from_db()
        assert product.stock == 3
        assert not user.cart.items.exists()

    def test_confirmation_email_is_sent(self, user_client, user, cart_item, django_capture_on_commit_callbacks):
        with django_capture_on_commit_callbacks(execute=True):
            user_client.post('/api/v1/orders/', ADDRESS)

        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == [user.email]
        assert 'Pending' in mail.outbox[0].subject

    def test_not_enough_stock(self, user_client, product, cart_item):
        product.stock = 1
        product.save()

        response = user_client.post('/api/v1/orders/', ADDRESS)

        assert response.status_code == 400
        assert not Order.objects.exists()
        product.refresh_from_db()
        assert product.stock == 1

    def test_price_is_copied_at_checkout(self, user_client, product, cart_item):
        order_id = user_client.post('/api/v1/orders/', ADDRESS).data['id']
        product.price = '999.00'
        product.save()

        response = user_client.get(f'/api/v1/orders/{order_id}/')

        assert response.data['items'][0]['price'] == '100.00'


@pytest.mark.django_db
class TestOrderAccess:
    def test_customer_sees_only_own_orders(self, user_client, user, product, cart_item):
        order_id = user_client.post('/api/v1/orders/', ADDRESS).data['id']
        other = UserFactory()
        CartItemFactory(cart__user=other, product=product)
        create_order(other, **ADDRESS)

        assert user_client.get('/api/v1/orders/').data['count'] == 1

        other_client = APIClient()
        other_client.force_authenticate(other)
        assert other_client.get(f'/api/v1/orders/{order_id}/').status_code == 404

    def test_staff_sees_all_orders(self, staff_client, user, product, cart_item):
        create_order(user, **ADDRESS)

        assert staff_client.get('/api/v1/orders/').data['count'] == 1


@pytest.mark.django_db
class TestOrderStatus:
    @pytest.fixture
    def order(self, user, product, cart_item):
        return create_order(user, **ADDRESS)

    def test_customer_can_cancel_pending_order(self, user_client, order, product):
        response = user_client.post(f'/api/v1/orders/{order.pk}/cancel/')

        assert response.status_code == 200
        assert response.data['status'] == 'cancelled'
        product.refresh_from_db()
        assert product.stock == 5

    def test_customer_cannot_cancel_paid_order(self, user_client, staff_client, order):
        staff_client.post(f'/api/v1/orders/{order.pk}/status/', {'status': 'paid'})

        assert user_client.post(f'/api/v1/orders/{order.pk}/cancel/').status_code == 400

    def test_customer_cannot_change_status(self, user_client, order):
        assert user_client.post(f'/api/v1/orders/{order.pk}/status/', {'status': 'paid'}).status_code == 403

    def test_staff_moves_order_through_statuses(self, staff_client, order):
        for status in ('paid', 'shipped', 'delivered'):
            response = staff_client.post(f'/api/v1/orders/{order.pk}/status/', {'status': status})
            assert response.status_code == 200
            assert response.data['status'] == status

    @pytest.mark.parametrize(('steps', 'bad_status'), (
        ((), 'shipped'),
        (('paid', 'shipped', 'delivered'), 'cancelled'),
        (('cancelled',), 'paid'),
    ))
    def test_invalid_transitions(self, staff_client, order, steps, bad_status):
        for status in steps:
            staff_client.post(f'/api/v1/orders/{order.pk}/status/', {'status': status})

        response = staff_client.post(f'/api/v1/orders/{order.pk}/status/', {'status': bad_status})

        assert response.status_code == 400


@pytest.mark.django_db
class TestCancelUnpaidOrders:
    def test_old_pending_orders_are_cancelled(self, user, product, cart_item):
        order = create_order(user, **ADDRESS)
        Order.objects.filter(pk=order.pk).update(created_at=timezone.now() - timedelta(hours=1))

        assert cancel_unpaid_orders() == 1

        order.refresh_from_db()
        product.refresh_from_db()
        assert order.status == Order.Status.CANCELLED
        assert product.stock == 5

    def test_fresh_and_paid_orders_are_kept(self, user, product, cart_item):
        fresh = create_order(user, **ADDRESS)
        CartItemFactory(cart__user=user, product=product)
        paid = create_order(user, **ADDRESS)
        Order.objects.filter(pk=paid.pk).update(
            status=Order.Status.PAID,
            created_at=timezone.now() - timedelta(hours=1),
        )

        assert cancel_unpaid_orders() == 0
        fresh.refresh_from_db()
        assert fresh.status == Order.Status.PENDING


@pytest.mark.django_db(transaction=True)
def test_last_item_cannot_be_sold_twice():
    """Five customers try to buy the last item at the same moment. Only one should succeed."""
    product = ProductFactory(stock=1)
    buyers = [UserFactory() for _ in range(5)]
    for buyer in buyers:
        CartItemFactory(cart__user=buyer, product=product)

    barrier = threading.Barrier(len(buyers))
    results = []

    def buy(buyer):
        barrier.wait()
        try:
            create_order(buyer, **ADDRESS)
            results.append('ok')
        except Exception:
            results.append('rejected')
        finally:
            connection.close()

    threads = [threading.Thread(target=buy, args=(buyer,)) for buyer in buyers]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    product.refresh_from_db()
    assert results.count('ok') == 1
    assert product.stock == 0
    assert Order.objects.count() == 1
