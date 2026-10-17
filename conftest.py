import pytest
from rest_framework.test import APIClient

from apps.common.tests.factories import CategoryFactory, ProductFactory, UserFactory


@pytest.fixture(autouse=True)
def _test_settings(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
    settings.PASSWORD_HASHERS = ('django.contrib.auth.hashers.MD5PasswordHasher',)
    # The test client talks plain HTTP, so don't redirect it to HTTPS when CI runs with DEBUG=0
    settings.SECURE_SSL_REDIRECT = False


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def staff(db):
    return UserFactory(is_staff=True)


@pytest.fixture
def user_client(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.fixture
def staff_client(staff):
    client = APIClient()
    client.force_authenticate(staff)
    return client


@pytest.fixture
def category(db):
    return CategoryFactory()


@pytest.fixture
def product(category):
    return ProductFactory(category=category, price='100.00', stock=5)
