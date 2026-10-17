from rest_framework import serializers

from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ('id', 'product', 'product_title', 'price', 'quantity', 'subtotal')


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = (
            'id', 'status', 'total_price', 'shipping_address', 'phone',
            'comment', 'items', 'created_at', 'updated_at',
        )


class CreateOrderSerializer(serializers.Serializer):
    shipping_address = serializers.CharField()
    phone = serializers.CharField(max_length=20)
    comment = serializers.CharField(required=False, allow_blank=True, default='')


class OrderStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Order.Status.choices)
