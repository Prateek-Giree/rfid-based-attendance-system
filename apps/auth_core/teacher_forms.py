import re
from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()

_NAME_RE = re.compile(r"^[a-zA-Z\s]+$")
_PHONE_RE = re.compile(r"^(97|98)\d{8}$")


class TeacherForm(forms.Form):
    """
    Combined form for creating and updating a Teacher.
    Spans two models: User (first_name, last_name, email) and Teacher (contact).
    Includes password fields for managing user login credentials.
    """

    first_name = forms.CharField(
        max_length=50,
        label="First Name",
        widget=forms.TextInput(
            attrs={
                "class": "input-field",
                "placeholder": "e.g., John",
                "data-validator": "name",
                "data-required": "true",
                "data-min": "2",
                "data-max": "50",
            }
        ),
    )

    last_name = forms.CharField(
        max_length=50,
        label="Last Name",
        widget=forms.TextInput(
            attrs={
                "class": "input-field",
                "placeholder": "e.g., Doe",
                "data-validator": "name",
                "data-required": "true",
                "data-min": "2",
                "data-max": "50",
            }
        ),
    )

    email = forms.EmailField(
        label="Email Address",
        widget=forms.EmailInput(
            attrs={
                "class": "input-field",
                "placeholder": "teacher@school.edu",
                "autocomplete": "off",
                "data-validator": "email",
                "data-required": "true",
            }
        ),
    )

    contact = forms.CharField(
        max_length=15,
        label="Contact Number",
        widget=forms.TextInput(
            attrs={
                "class": "input-field",
                "placeholder": "e.g., 9812345678",
                "data-validator": "phone",
                "data-required": "true",
            }
        ),
    )

    password1 = forms.CharField(
        required=False,
        label="Password",
        widget=forms.PasswordInput(
            attrs={
                "class": "input-field",
                "placeholder": "••••••••",
                "id": "id_password1",
                "data-validator": "password",
            }
        ),
    )

    password2 = forms.CharField(
        required=False,
        label="Confirm Password",
        widget=forms.PasswordInput(
            attrs={
                "class": "input-field",
                "placeholder": "••••••••",
                "data-validator": "password-confirm",
                "data-match-field": "id_password1",
            }
        ),
    )

    def __init__(self, *args, teacher_instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._teacher_instance = teacher_instance

        if teacher_instance:
            self.fields["first_name"].initial = teacher_instance.user.first_name
            self.fields["last_name"].initial = teacher_instance.user.last_name
            self.fields["email"].initial = teacher_instance.user.email
            self.fields["contact"].initial = teacher_instance.contact

    # ── Field-level validators ────────────────────────────────────────────────

    def clean_first_name(self):
        value = self.cleaned_data.get("first_name", "").strip()
        if not value:
            raise forms.ValidationError("First name is required.")
        if len(value) < 2:
            raise forms.ValidationError("First name must be at least 2 characters.")
        if len(value) > 50:
            raise forms.ValidationError("First name must be no more than 50 characters.")
        if not _NAME_RE.match(value):
            raise forms.ValidationError("First name may only contain letters and spaces.")
        return value

    def clean_last_name(self):
        value = self.cleaned_data.get("last_name", "").strip()
        if not value:
            raise forms.ValidationError("Last name is required.")
        if len(value) < 2:
            raise forms.ValidationError("Last name must be at least 2 characters.")
        if len(value) > 50:
            raise forms.ValidationError("Last name must be no more than 50 characters.")
        if not _NAME_RE.match(value):
            raise forms.ValidationError("Last name may only contain letters and spaces.")
        return value

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip()
        qs = User.objects.filter(email__iexact=email)
        if self._teacher_instance:
            qs = qs.exclude(pk=self._teacher_instance.user.pk)
        if qs.exists():
            raise forms.ValidationError(
                "A user with this email address already exists."
            )
        return email

    def clean_contact(self):
        value = self.cleaned_data.get("contact", "").strip()
        if not value:
            raise forms.ValidationError("Contact number is required.")
        if not _PHONE_RE.match(value):
            raise forms.ValidationError(
                "Enter a valid 10-digit number starting with 97 or 98."
            )
        return value

    # ── Cross-field validator ─────────────────────────────────────────────────

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if not self._teacher_instance:
            if not password1:
                self.add_error("password1", "Password is required.")
            if not password2:
                self.add_error("password2", "Confirm Password is required.")

        if password1 or password2:
            if password1 != password2:
                self.add_error("password2", "Passwords do not match.")
            if password1 and len(password1) < 8:
                self.add_error("password1", "Password must be at least 8 characters.")

        return cleaned_data
