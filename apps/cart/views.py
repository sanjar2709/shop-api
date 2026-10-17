from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Cart
from .serializers import AddCartItemSerializer, CartSerializer, UpdateCartItemSerializer


def get_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return Cart.objects.prefetch_related('items__product').get(pk=cart.pk)


class CartView(APIView):
    @extend_schema(responses=CartSerializer)
    def get(self, request):
        return Response(CartSerializer(get_cart(request.user)).data)

    @extend_schema(responses={204: None})
    def delete(self, request):
        get_cart(request.user).items.all().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CartItemListView(APIView):
    @extend_schema(request=AddCartItemSerializer, responses={201: CartSerializer})
    def post(self, request):
        cart = get_cart(request.user)
        serializer = AddCartItemSerializer(data=request.data, context={'cart': cart})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(CartSerializer(get_cart(request.user)).data, status=status.HTTP_201_CREATED)


class CartItemDetailView(APIView):
    @extend_schema(request=UpdateCartItemSerializer, responses=CartSerializer)
    def patch(self, request, pk):
        cart = get_cart(request.user)
        item = get_object_or_404(cart.items.select_related('product'), pk=pk)
        serializer = UpdateCartItemSerializer(item, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(CartSerializer(get_cart(request.user)).data)

    @extend_schema(responses={204: None})
    def delete(self, request, pk):
        cart = get_cart(request.user)
        get_object_or_404(cart.items, pk=pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
