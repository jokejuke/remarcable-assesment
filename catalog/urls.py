from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.ProductListView.as_view(), name="product-list"),
    path("products/<int:product_id>/favorite/", views.favorite_add, name="favorite-add"),
    path("products/<int:product_id>/unfavorite/", views.favorite_remove, name="favorite-remove"),
    path("products/<int:product_id>/buy/", views.buy, name="buy"),
    path("me/favorites/", views.MyFavoritesView.as_view(), name="my-favorites"),
    path("me/orders/", views.MyOrdersView.as_view(), name="my-orders"),
]
