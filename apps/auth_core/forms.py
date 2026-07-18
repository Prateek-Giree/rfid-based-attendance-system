from django.contrib.auth.forms import AuthenticationForm
from django import forms


class LoginForm(AuthenticationForm):
    """
    Custom login form using email (USERNAME_FIELD) instead of username.
    Tailwind classes are applied via widget attrs.
    """

    username = forms.EmailField(
        label="Email Address",
        widget=forms.EmailInput(
            attrs={
                "class": "input-field",
                "placeholder": "you@example.com",
                "autocomplete": "email",
                "autofocus": True,
            }
        ),
    )

    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={
                "class": "input-field",
                "placeholder": "••••••••",
                "autocomplete": "current-password",
            }
        ),
    )
