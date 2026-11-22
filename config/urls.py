from django.contrib import admin
from django.urls import include, path

from catalog.accounts import DemoLoginView, signup

urlpatterns = [
    path("admin/", admin.site.urls),
    # These two come first so they take precedence over the stock routes below.
    path("accounts/login/", DemoLoginView.as_view(), name="login"),
    path("accounts/signup/", signup, name="signup"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("api/", include("catalog.api.urls")),
    path("", include("catalog.urls")),
]
