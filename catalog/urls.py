from django.urls import path

from catalog import views

app_name = "catalog"

urlpatterns = [
    path("", views.ProductListView.as_view(), name="product-list"),
    path("products/<slug:slug>/", views.ProductDetailView.as_view(), name="product-detail"),
    path("products/<int:product_id>/buy/", views.buy, name="buy"),
    path("me/favorites/", views.MyFavoritesView.as_view(), name="my-favorites"),
    path("me/orders/", views.MyOrdersView.as_view(), name="my-orders"),
]
