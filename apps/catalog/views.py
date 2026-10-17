from rest_framework import viewsets

from apps.common.permissions import IsStaffOrReadOnly

from .filters import ProductFilter
from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = (IsStaffOrReadOnly,)
    lookup_field = 'slug'
    pagination_class = None

    def get_queryset(self):
        qs = Category.objects.all()
        # Customers only see active categories, staff see everything
        if not self.request.user.is_staff:
            qs = qs.filter(is_active=True)
        return qs


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = (IsStaffOrReadOnly,)
    lookup_field = 'slug'
    filterset_class = ProductFilter
    search_fields = ('title', 'description')
    ordering_fields = ('price', 'created_at', 'title')

    def get_queryset(self):
        qs = Product.objects.select_related('category')
        if not self.request.user.is_staff:
            qs = qs.filter(is_active=True, category__is_active=True)
        return qs
