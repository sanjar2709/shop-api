from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import TimeStampedModel


class Category(TimeStampedModel):
    title = models.CharField(_('Title'), max_length=100, unique=True)
    slug = models.SlugField(_('Slug'), max_length=120, unique=True)
    is_active = models.BooleanField(_('Is active'), default=True)

    class Meta:
        ordering = ('title',)
        verbose_name = _('Category')
        verbose_name_plural = _('Categories')

    def __str__(self):
        return self.title


class Product(TimeStampedModel):
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name=_('Category'),
    )
    title = models.CharField(_('Title'), max_length=200)
    slug = models.SlugField(_('Slug'), max_length=220, unique=True)
    description = models.TextField(_('Description'), blank=True)
    price = models.DecimalField(_('Price'), max_digits=12, decimal_places=2, validators=(MinValueValidator(0),))
    stock = models.PositiveIntegerField(_('Stock'), default=0)
    is_active = models.BooleanField(_('Is active'), default=True)

    class Meta:
        ordering = ('-created_at',)
        verbose_name = _('Product')
        verbose_name_plural = _('Products')
        indexes = (
            models.Index(fields=('is_active', 'category')),
            models.Index(fields=('price',)),
        )

    def __str__(self):
        return self.title

    @property
    def in_stock(self):
        return self.stock > 0
