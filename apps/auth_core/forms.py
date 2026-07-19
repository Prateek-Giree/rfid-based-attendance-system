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
                "data-validator": "email",
                "data-required": "true",
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
                "data-validator": "password",
                "data-required": "true",
            }
        ),
    )


class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(
        label="Email Address",
        widget=forms.EmailInput(
            attrs={
                "class": "input-field",
                "placeholder": "you@example.com",
                "autocomplete": "email",
                "autofocus": True,
                "data-validator": "email",
                "data-required": "true",
            }
        ),
    )


class VerifyOTPForm(forms.Form):
    otp_code = forms.CharField(
        label="Enter OTP",
        max_length=6,
        min_length=6,
        widget=forms.TextInput(
            attrs={
                "class": "input-field text-center tracking-widest font-mono text-xl",
                "placeholder": "------",
                "autocomplete": "one-time-code",
                "autofocus": True,
                "data-validator": "otp",
                "data-required": "true",
                "inputmode": "numeric",
            }
        ),
    )


class ResetPasswordForm(forms.Form):
    new_password = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(
            attrs={
                "id": "new_password",
                "class": "input-field",
                "placeholder": "••••••••",
                "autocomplete": "new-password",
                "data-validator": "password",
                "data-required": "true",
            }
        ),
    )
    confirm_password = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(
            attrs={
                "class": "input-field",
                "placeholder": "••••••••",
                "autocomplete": "new-password",
                "data-validator": "password-confirm",
                "data-match-field": "new_password",
                "data-required": "true",
            }
        ),
    )
