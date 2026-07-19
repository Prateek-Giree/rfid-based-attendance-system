from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()


class TeacherForm(forms.Form):
    """
    Combined form for creating and updating a Teacher.
    Spans two models: User (first_name, last_name, email) and Teacher (contact).
    Includes password fields for managing user login credentials.
    """

    first_name = forms.CharField(
        max_length=150,
        label="First Name",
        widget=forms.TextInput(
            attrs={"class": "input-field", "placeholder": "e.g., John"}
        ),
    )

    last_name = forms.CharField(
        max_length=150,
        label="Last Name",
        widget=forms.TextInput(
            attrs={"class": "input-field", "placeholder": "e.g., Doe"}
        ),
    )

    email = forms.EmailField(
        label="Email Address",
        widget=forms.EmailInput(
            attrs={
                "class": "input-field",
                "placeholder": "teacher@school.edu",
                "autocomplete": "off",
            }
        ),
    )

    contact = forms.CharField(
        max_length=20,
        label="Contact Number",
        widget=forms.TextInput(
            attrs={"class": "input-field", "placeholder": "e.g., +977 98XXXXXXXX"}
        ),
    )

    password1 = forms.CharField(
        required=False,
        label="Password",
        widget=forms.PasswordInput(
            attrs={"class": "input-field", "placeholder": "••••••••"}
        ),
    )

    password2 = forms.CharField(
        required=False,
        label="Confirm Password",
        widget=forms.PasswordInput(
            attrs={"class": "input-field", "placeholder": "••••••••"}
        ),
    )

    def __init__(self, *args, teacher_instance=None, **kwargs):
        """
        Accept an optional teacher_instance to populate initial values for edit.
        """
        super().__init__(*args, **kwargs)
        self._teacher_instance = teacher_instance

        if teacher_instance:
            self.fields["first_name"].initial = teacher_instance.user.first_name
            self.fields["last_name"].initial = teacher_instance.user.last_name
            self.fields["email"].initial = teacher_instance.user.email
            self.fields["contact"].initial = teacher_instance.contact

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

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        # Password required only when creating a new teacher
        if not self._teacher_instance:
            if not password1:
                self.add_error("password1", "Password is required.")
            if not password2:
                self.add_error("password2", "Confirm Password is required.")

        # Validate complexity and match if password was provided
        if password1 or password2:
            if password1 != password2:
                self.add_error("password2", "Passwords do not match.")
            if password1 and len(password1) < 8:
                self.add_error("password1", "Password must be at least 8 characters.")

        return cleaned_data
