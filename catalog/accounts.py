"""Sign-up and login by email address. The email is the username (stored in lower case)."""

from django import forms
from django.contrib.auth import get_user_model, login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render

from catalog.views import safe_next

User = get_user_model()


class EmailAuthenticationForm(AuthenticationForm):
    """Login form: the first field is an email, matched ignoring letter case.

    Every stored username is lower case (sign-up and the demo accounts), so lower-casing the
    input is enough; no custom authentication backend is needed, and the admin login and the
    API token endpoint keep exact matching.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Email"

    def clean_username(self):
        return self.cleaned_data["username"].strip().lower()


class SignUpForm(forms.Form):
    email = forms.EmailField(label="Email", max_length=150)  # 150 = the username length limit
    password1 = forms.CharField(label="Password", strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    password2 = forms.CharField(
        label="Repeat password", strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "new-password"})
    )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(username__iexact=email).exists():
            raise ValidationError("This email is already registered.")
        return email

    def clean(self):
        cleaned = super().clean()
        password1, password2 = cleaned.get("password1"), cleaned.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "The two passwords don't match.")
        elif password1:
            email = cleaned.get("email", "")
            try:
                validate_password(password1, user=User(username=email, email=email))
            except ValidationError as error:
                self.add_error("password1", error)
        return cleaned

    def save(self):
        email = self.cleaned_data["email"]
        return User.objects.create_user(username=email, email=email, password=self.cleaned_data["password1"])


def signup(request):
    """Create a regular (non-staff) account, log the visitor in and send them back to `next`."""
    if request.user.is_authenticated:
        return redirect("catalog:product-list")
    form = SignUpForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                user = form.save()
        except IntegrityError:  # someone registered the same email a moment ago
            form.add_error("email", "This email is already registered.")
        else:
            login(request, user)
            return redirect(safe_next(request))
    next_url = request.POST.get("next") or request.GET.get("next") or ""
    return render(request, "registration/signup.html", {"form": form, "next": next_url})
