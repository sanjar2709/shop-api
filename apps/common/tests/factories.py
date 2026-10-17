import factory

from apps.cart.models import Cart, CartItem
from apps.catalog.models import Category, Product
from apps.users.models import User


class UserFactory(factory.django.DjangoModelFactory):
    email = factory.Sequence(lambda n: f'user{n}@example.com')
    password = factory.django.Password('Str0ngPass!42')

    class Meta:
        model = User


class CategoryFactory(factory.django.DjangoModelFactory):
    title = factory.Sequence(lambda n: f'Category {n}')
    slug = factory.Sequence(lambda n: f'category-{n}')

    class Meta:
        model = Category


class ProductFactory(factory.django.DjangoModelFactory):
    category = factory.SubFactory(CategoryFactory)
    title = factory.Sequence(lambda n: f'Product {n}')
    slug = factory.Sequence(lambda n: f'product-{n}')
    price = '10.00'
    stock = 10

    class Meta:
        model = Product


class CartFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)

    class Meta:
        model = Cart
        django_get_or_create = ('user',)


class CartItemFactory(factory.django.DjangoModelFactory):
    cart = factory.SubFactory(CartFactory)
    product = factory.SubFactory(ProductFactory)
    quantity = 1

    class Meta:
        model = CartItem
