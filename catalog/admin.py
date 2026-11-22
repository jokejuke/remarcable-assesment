"""Admin: the only write path for categories, tags and products."""

from django import forms
from django.contrib import admin
from django.db.models import Count

from catalog.category_tree import get_category_tree
from catalog.models import Category, Favorite, Order, OrderItem, Product, Tag
from catalog.templatetags.money import format_cents, format_unix


class TimestampsMixin:
    """Shows the Unix-second timestamps as readable dates."""

    @admin.display(description="Created")
    def created(self, obj):
        return format_unix(obj.created_at) if obj.pk else "-"

    @admin.display(description="Updated")
    def updated(self, obj):
        return format_unix(obj.updated_at) if obj.pk else "-"


# --- Categories --------------------------------------------------------------

KIND_PRODUCTS = "products"
KIND_SUBCATEGORIES = "subcategories"


class CategoryAdminForm(forms.ModelForm):
    """Edits the two kind flags through one radio choice."""

    kind = forms.ChoiceField(
        label="Holds",
        choices=[(KIND_PRODUCTS, "Products"), (KIND_SUBCATEGORIES, "Subcategories")],
        widget=forms.RadioSelect,
        initial=KIND_PRODUCTS,
    )

    class Meta:
        model = Category
        fields = ["name", "parent", "kind"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial["kind"] = KIND_SUBCATEGORIES if self.instance.has_subcategories else KIND_PRODUCTS
        tree = get_category_tree()
        self.fields["parent"].label_from_instance = lambda c: tree.path(c.pk) or c.name

    def _post_clean(self):
        # Set the flags before model validation runs in super()._post_clean().
        kind = self.cleaned_data.get("kind")
        if kind:
            self.instance.has_products = kind == KIND_PRODUCTS
            self.instance.has_subcategories = kind == KIND_SUBCATEGORIES
        super()._post_clean()


@admin.register(Category)
class CategoryAdmin(TimestampsMixin, admin.ModelAdmin):
    form = CategoryAdminForm
    list_display = ["full_path", "holds", "product_count", "updated"]
    search_fields = ["name"]
    readonly_fields = ["created", "updated"]
    fields = ["name", "parent", "kind", "created", "updated"]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(n_products=Count("products"))

    @admin.display(description="Category", ordering="name")
    def full_path(self, obj):
        return get_category_tree().path(obj.pk) or obj.name

    @admin.display(description="Holds")
    def holds(self, obj):
        return "Products" if obj.has_products else "Subcategories"

    @admin.display(description="Products", ordering="n_products")
    def product_count(self, obj):
        return obj.n_products


# --- Tags and products -------------------------------------------------------


@admin.register(Tag)
class TagAdmin(TimestampsMixin, admin.ModelAdmin):
    list_display = ["name", "product_count", "updated"]
    search_fields = ["name"]
    readonly_fields = ["created", "updated"]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(n_products=Count("products"))

    @admin.display(description="Products", ordering="n_products")
    def product_count(self, obj):
        return obj.n_products


@admin.register(Product)
class ProductAdmin(TimestampsMixin, admin.ModelAdmin):
    list_display = ["name", "category_path", "price", "items_available", "updated"]
    list_filter = ["category", "tags"]
    search_fields = ["name", "description"]
    list_select_related = ["category"]
    filter_horizontal = ["tags"]
    readonly_fields = ["created", "updated"]
    fields = [
        "name", "slug", "image_url", "description", "price_cents", "items_available", "category", "tags",
        "created", "updated",
    ]
    prepopulated_fields = {"slug": ["name"]}  # only while adding, so a rename never rewrites the slug

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == "category":
            tree = get_category_tree()
            field.label_from_instance = lambda c: tree.path(c.pk) or c.name
        return field

    @admin.display(description="Category", ordering="category__name")
    def category_path(self, obj):
        return get_category_tree().path(obj.category_id)

    @admin.display(description="Price", ordering="price_cents")
    def price(self, obj):
        return format_cents(obj.price_cents)


# --- Favourites and orders ---------------------------------------------------


@admin.register(Favorite)
class FavoriteAdmin(TimestampsMixin, admin.ModelAdmin):
    list_display = ["user", "product", "created"]
    list_select_related = ["user", "product"]
    search_fields = ["user__username", "product__name"]
    raw_id_fields = ["user", "product"]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    fields = ["product", "quantity", "unit_price", "line_total"]
    readonly_fields = fields
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description="Unit price")
    def unit_price(self, obj):
        return format_cents(obj.unit_price_cents)

    @admin.display(description="Subtotal")
    def line_total(self, obj):
        return format_cents(obj.line_total_cents)


@admin.register(Order)
class OrderAdmin(TimestampsMixin, admin.ModelAdmin):
    """Orders are a record of what was bought: view-only."""

    list_display = ["__str__", "user", "total", "created"]
    list_select_related = ["user"]
    search_fields = ["user__username"]
    fields = ["user", "total", "created", "updated"]
    readonly_fields = fields
    inlines = [OrderItemInline]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Total", ordering="total_cents")
    def total(self, obj):
        return format_cents(obj.total_cents)
