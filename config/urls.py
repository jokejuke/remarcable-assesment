from django.contrib import admin
from django.contrib.auth.views import LoginView
from django.urls import include, path

from catalog.accounts import EmailAuthenticationForm, signup

urlpatterns = [
    path("admin/", admin.site.urls),
    # These two come first so they take precedence over the stock routes below.
    path("accounts/login/", LoginView.as_view(authentication_form=EmailAuthenticationForm), name="login"),
    path("accounts/signup/", signup, name="signup"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("api/", include("catalog.api.urls")),
    path("", include("catalog.urls")),
]
