from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from catalog.category_tree import get_category_tree
from catalog.models import Category, Favorite, Order, OrderItem, Product, Tag
from catalog.templatetags.money import format_cents


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name"]


class CategorySerializer(serializers.ModelSerializer):
    path = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "parent", "path", "has_products", "has_subcategories", "created_at", "updated_at"]

    def get_path(self, obj) -> str:
        return get_category_tree().path(obj.pk)


class CategoryRefSerializer(serializers.ModelSerializer):
    path = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "path"]

    def get_path(self, obj) -> str:
        return get_category_tree().path(obj.pk)


class ProductSerializer(serializers.ModelSerializer):
    price = serializers.SerializerMethodField(help_text='Formatted price, e.g. "$49.00".')
    category = CategoryRefSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    is_favorite = serializers.SerializerMethodField(help_text="Only present for authenticated users.")

    class Meta:
        model = Product
        fields = [
            "id", "slug", "name", "description", "price_cents", "price", "items_available", "image_url",
            "category", "tags", "is_favorite", "created_at", "updated_at",
        ]

    def get_price(self, obj) -> str:
        return format_cents(obj.price_cents)

    @extend_schema_field(serializers.BooleanField(required=False))
    def get_is_favorite(self, obj):
        return bool(getattr(obj, "is_favorite", False))

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            data.pop("is_favorite", None)
        return data


class FavoriteSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())

    class Meta:
        model = Favorite
        fields = ["product", "created_at"]
        read_only_fields = ["created_at"]
        validators = []  # the view handles duplicates (returns 200)


class FavoriteDetailSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)

    class Meta:
        model = Favorite
        fields = ["product", "created_at"]


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = OrderItem
        fields = ["product", "product_name", "quantity", "unit_price_cents"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ["id", "items", "total_cents", "total", "created_at"]

    def get_total(self, obj) -> str:
        return format_cents(obj.total_cents)


class OrderItemInputSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    quantity = serializers.IntegerField(min_value=1, max_value=1000)


class OrderCreateSerializer(serializers.Serializer):
    items = OrderItemInputSerializer(many=True, allow_empty=False)

    def validate_items(self, items):
        ids = [item["product"].pk for item in items]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError("Each product can appear only once per order.")
        return items


class OutOfStockSerializer(serializers.Serializer):
    out_of_stock = serializers.ListField(child=serializers.IntegerField(), help_text="Ids of products lacking stock.")


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Token login by email and password. The email is the account's username, matched ignoring case."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        del self.fields[self.username_field]
        self.fields["email"] = serializers.EmailField(write_only=True, max_length=150)

    def validate(self, attrs):
        credentials = {self.username_field: attrs["email"].strip().lower(), "password": attrs["password"]}
        return super().validate(credentials)


class TokenPairSerializer(serializers.Serializer):
    access = serializers.CharField(help_text="Short-lived token for the `Authorization: Bearer` header.")
    refresh = serializers.CharField(help_text="Long-lived token for `/api/auth/token/refresh/` and logout.")
