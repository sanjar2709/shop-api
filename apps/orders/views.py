from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from . import services
from .models import Order
from .serializers import CreateOrderSerializer, OrderSerializer, OrderStatusSerializer


class OrderViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = OrderSerializer
    filterset_fields = ('status',)
    ordering_fields = ('created_at', 'total_price')

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Order.objects.none()
        qs = Order.objects.prefetch_related('items')
        # Staff can see all orders, customers only their own
        if not self.request.user.is_staff:
            qs = qs.filter(user=self.request.user)
        return qs

    @extend_schema(request=CreateOrderSerializer, responses={201: OrderSerializer})
    def create(self, request):
        serializer = CreateOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = services.create_order(request.user, **serializer.validated_data)
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=None, responses=OrderSerializer)
    @action(detail=True, methods=('post',))
    def cancel(self, request, pk=None):
        order = self.get_object()
        # A customer can cancel only before payment, after that it goes through staff (refund)
        if not request.user.is_staff and order.status != Order.Status.PENDING:
            raise ValidationError({'status': _('Only pending orders can be cancelled.')})
        order = services.change_status(order, Order.Status.CANCELLED)
        return Response(OrderSerializer(order).data)

    @extend_schema(request=OrderStatusSerializer, responses=OrderSerializer)
    @action(detail=True, methods=('post',), permission_classes=(permissions.IsAdminUser,))
    def status(self, request, pk=None):
        serializer = OrderStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = services.change_status(self.get_object(), serializer.validated_data['status'])
        return Response(OrderSerializer(order).data)
