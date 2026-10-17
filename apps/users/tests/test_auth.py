import pytest

from apps.users.models import User

pytestmark = pytest.mark.django_db

PASSWORD = 'Str0ngPass!42'


def test_register(api_client):
    response = api_client.post('/api/v1/auth/register/', {'email': 'new@example.com', 'password': PASSWORD})

    assert response.status_code == 201
    assert 'password' not in response.data
    assert User.objects.get(email='new@example.com').check_password(PASSWORD)


def test_register_rejects_weak_password(api_client):
    response = api_client.post('/api/v1/auth/register/', {'email': 'new@example.com', 'password': '123'})

    assert response.status_code == 400
    assert 'password' in response.data


def test_register_rejects_duplicate_email(api_client, user):
    response = api_client.post('/api/v1/auth/register/', {'email': user.email, 'password': PASSWORD})

    assert response.status_code == 400


def test_login_returns_tokens(api_client, user):
    response = api_client.post('/api/v1/auth/login/', {'email': user.email, 'password': PASSWORD})

    assert response.status_code == 200
    assert {'access', 'refresh'} <= response.data.keys()


def test_login_with_wrong_password(api_client, user):
    response = api_client.post('/api/v1/auth/login/', {'email': user.email, 'password': 'wrong'})

    assert response.status_code == 401


def test_logout_blacklists_refresh_token(api_client, user):
    tokens = api_client.post('/api/v1/auth/login/', {'email': user.email, 'password': PASSWORD}).data

    response = api_client.post('/api/v1/auth/logout/', {'refresh': tokens['refresh']})
    assert response.status_code == 200

    response = api_client.post('/api/v1/auth/refresh/', {'refresh': tokens['refresh']})
    assert response.status_code == 401


def test_me_requires_auth(api_client):
    assert api_client.get('/api/v1/auth/me/').status_code == 401


def test_me_update(user_client, user):
    response = user_client.patch('/api/v1/auth/me/', {'first_name': 'Sanjar', 'email': 'hacker@example.com'})

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.first_name == 'Sanjar'
    # email is read-only
    assert user.email != 'hacker@example.com'
