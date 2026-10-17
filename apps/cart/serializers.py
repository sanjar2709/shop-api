from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.catalog.models import Product

from .models import Cart, CartItem


class CartProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ('id', 'title', 'slug', 'price', 'stock')


class CartItemSerializer(serializers.ModelSerializer):
    product = CartProductSerializer(read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = ('id', 'product', 'quantity', 'subtotal')


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Cart
        fields = ('id', 'items', 'total_price', 'updated_at')


class AddCartItemSerializer(serializers.Serializer):
    product = serializers.SlugRelatedField(
        slug_field='slug',
        queryset=Product.objects.filter(is_active=True, category__is_active=True),
    )
    quantity = serializers.IntegerField(min_value=1, default=1)

    def validate(self, attrs):
        cart = self.context['cart']
        product = attrs['product']
        item = cart.items.filter(product=product).first()
        total = attrs['quantity'] + (item.quantity if item else 0)
        if total > product.stock:
            raise serializers.ValidationError({'quantity': _('Only %(stock)s left in stock.') % {'stock': product.stock}})
        return attrs

    def save(self):
        cart = self.context['cart']
        item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=self.validated_data['product'],
            defaults={'quantity': self.validated_data['quantity']},
        )
        if not created:
            item.quantity += self.validated_data['quantity']
            item.save(update_fields=('quantity', 'updated_at'))
        return item


class UpdateCartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = ('quantity',)

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError(_('Quantity must be at least 1.'))
        if value > self.instance.product.stock:
            raise serializers.ValidationError(_('Only %(stock)s left in stock.') % {'stock': self.instance.product.stock})
        return value
