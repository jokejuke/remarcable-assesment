from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.exceptions import APIException, NotAuthenticated
from rest_framework.response import Response

from catalog.filters import ProductFilterSet
from catalog.models import Category, Favorite, Order, Product, Tag
from catalog.services import OutOfStock, place_order

from . import serializers as s


class OutOfStockError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Not enough stock."
    default_code = "out_of_stock"

    def __init__(self, product_ids):
        super().__init__()
        self.detail = {"out_of_stock": product_ids}


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """Products, filtered with the same parameters as the storefront."""

    serializer_class = s.ProductSerializer
    permission_classes = [permissions.AllowAny]
    filterset_class = ProductFilterSet

    def get_queryset(self):
        return Product.objects.for_listing(self.request.user)

    def filter_queryset(self, queryset):
        # The only-favourites filter needs a user; say so instead of ignoring it.
        if self.action == "list" and not self.request.user.is_authenticated:
            value = self.request.query_params.get("favorites", "").lower()
            if value in {"true", "1"}:
                raise NotAuthenticated("Log in to filter by favourites.")
        if self.action != "list":
            return queryset  # detail views show any product, in stock or not
        return super().filter_queryset(queryset)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """The category tree; `path` is the full label from the top level."""

    queryset = Category.objects.order_by("name")
    serializer_class = s.CategorySerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = []


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.order_by("name")
    serializer_class = s.TagSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = []


product_id_param = OpenApiParameter("product_id", int, OpenApiParameter.PATH, description="Product id.")


@extend_schema_view(
    list=extend_schema(responses=s.FavoriteDetailSerializer(many=True)),
    create=extend_schema(
        request=s.FavoriteSerializer,
        responses={201: s.FavoriteSerializer, 200: OpenApiResponse(s.FavoriteSerializer, "Already a favourite.")},
    ),
    destroy=extend_schema(
        parameters=[product_id_param],
        responses={204: OpenApiResponse(description="Removed (or was not a favourite).")},
    ),
)
class FavoriteViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """The current user's favourites. Add by product id; remove with DELETE `/api/favorites/{product_id}/`."""

    lookup_field = "product_id"
    lookup_value_regex = r"\d+"
    filter_backends = []

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):  # schema generation has no user
            return Favorite.objects.none()
        return (
            Favorite.objects.filter(user=self.request.user)
            .select_related("product__category")
            .prefetch_related("product__tags")
        )

    def get_serializer_class(self):
        return s.FavoriteDetailSerializer if self.action == "list" else s.FavoriteSerializer

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        # Every listed product is a favourite.
        results = response.data["results"] if isinstance(response.data, dict) else response.data
        for row in results:
            row["product"]["is_favorite"] = True
        return response

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        favorite, created = Favorite.objects.get_or_create(user=request.user, product=serializer.validated_data["product"])
        return Response(
            s.FavoriteSerializer(favorite).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )

    def destroy(self, request, *args, **kwargs):
        Favorite.objects.filter(user=request.user, product_id=kwargs["product_id"]).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    create=extend_schema(
        request=s.OrderCreateSerializer,
        responses={
            201: s.OrderSerializer,
            409: OpenApiResponse(s.OutOfStockSerializer, "One or more products lack stock; nothing was ordered."),
        },
    ),
)
class OrderViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    """The current user's orders. Placing an order is all-or-nothing."""

    serializer_class = s.OrderSerializer
    filter_backends = []

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):  # schema generation has no user
            return Order.objects.none()
        return Order.objects.filter(user=self.request.user).prefetch_related("items__product")

    def create(self, request, *args, **kwargs):
        serializer = s.OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        items = [(item["product"].pk, item["quantity"]) for item in serializer.validated_data["items"]]
        try:
            order = place_order(request.user, items)
        except OutOfStock as exc:
            raise OutOfStockError(exc.product_ids) from exc
        order = self.get_queryset().get(pk=order.pk)
        return Response(s.OrderSerializer(order).data, status=status.HTTP_201_CREATED)
