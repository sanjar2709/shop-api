from rest_framework import serializers

from .models import Category, Product


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'title', 'slug', 'is_active')


class ProductSerializer(serializers.ModelSerializer):
    category = serializers.SlugRelatedField(slug_field='slug', queryset=Category.objects.all())
    in_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Product
        fields = ('id', 'title', 'slug', 'description', 'category',
                  'price', 'stock', 'in_stock', 'is_active', 'created_at', 'updated_at',)
        read_only_fields = ('created_at', 'updated_at')
