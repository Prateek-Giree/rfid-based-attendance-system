import re
from django import forms
from .models import Classroom, Student
from apps.auth_core.models import Teacher

_NAME_RE = re.compile(r"^[a-zA-Z\s]+$")
_PHONE_RE = re.compile(r"^(97|98)\d{8}$")


class ClassroomForm(forms.ModelForm):

    class_teacher = forms.ModelChoiceField(
        queryset=Teacher.objects.all().select_related("user"),
        required=False,
        empty_label="Unassigned",
        label="Class Teacher",
        widget=forms.Select(attrs={"class": "input-field"}),
    )

    class Meta:
        model = Classroom
        fields = ["name", "section", "class_teacher"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "input-field",
                    "placeholder": "e.g., Class 10",
                    "autocomplete": "off",
                    "data-validator": "text-length",
                    "data-required": "true",
                    "data-max": "50",
                }
            ),
            "section": forms.TextInput(
                attrs={
                    "class": "input-field",
                    "placeholder": "e.g., A",
                    "autocomplete": "off",
                    "data-validator": "text-length",
                    "data-required": "true",
                    "data-max": "10",
                }
            ),
        }

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        if not name:
            raise forms.ValidationError("Classroom name is required.")
        if len(name) > 50:
            raise forms.ValidationError("Classroom name must be no more than 50 characters.")
        return name

    def clean_section(self):
        section = self.cleaned_data.get("section", "").strip()
        if not section:
            raise forms.ValidationError("Section is required.")
        if len(section) > 10:
            raise forms.ValidationError("Section must be no more than 10 characters.")
        return section

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get("name")
        section = cleaned_data.get("section")

        if name and section:
            qs = Classroom.objects.filter(name__iexact=name, section__iexact=section)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    f"A classroom named '{name}' with section '{section}' already exists."
                )

        return cleaned_data


class StudentForm(forms.ModelForm):

    classroom = forms.ModelChoiceField(
        queryset=Classroom.objects.all(),
        empty_label="Select Classroom",
        label="Classroom",
        widget=forms.Select(attrs={"class": "input-field", "data-validator": "required", "data-required": "true"}),
    )

    class Meta:
        model = Student
        fields = [
            "roll_no",
            "first_name",
            "last_name",
            "classroom",
            "rfid_uid",
            "contact",
            "address",
            "guardian_name",
            "guardian_contact",
            "is_active",
        ]
        widgets = {
            "roll_no": forms.NumberInput(
                attrs={
                    "class": "input-field",
                    "placeholder": "e.g., 12",
                    "min": "1",
                    "max": "9999",
                    "data-validator": "roll-no",
                    "data-required": "true",
                }
            ),
            "first_name": forms.TextInput(
                attrs={
                    "class": "input-field",
                    "placeholder": "John",
                    "data-validator": "name",
                    "data-required": "true",
                    "data-min": "2",
                    "data-max": "50",
                }
            ),
            "last_name": forms.TextInput(
                attrs={
                    "class": "input-field",
                    "placeholder": "Doe",
                    "data-validator": "name",
                    "data-required": "true",
                    "data-min": "2",
                    "data-max": "50",
                }
            ),
            "rfid_uid": forms.TextInput(
                attrs={
                    "class": "input-field font-mono",
                    "placeholder": "e.g., A1B2C3D4",
                    "data-validator": "rfid",
                    "data-required": "true",
                }
            ),
            "contact": forms.TextInput(
                attrs={
                    "class": "input-field",
                    "placeholder": "e.g., 9812345678",
                    "data-validator": "phone",
                    "data-phone-optional": "true",
                }
            ),
            "address": forms.Textarea(
                attrs={
                    "class": "input-field h-20 resize-none",
                    "placeholder": "Enter street address...",
                    "data-validator": "text-length",
                    "data-max": "500",
                }
            ),
            "guardian_name": forms.TextInput(
                attrs={
                    "class": "input-field",
                    "placeholder": "Jane Doe",
                    "data-validator": "name-long",
                    "data-required": "true",
                    "data-min": "2",
                    "data-max": "100",
                }
            ),
            "guardian_contact": forms.TextInput(
                attrs={
                    "class": "input-field",
                    "placeholder": "e.g., 9812345678",
                    "data-validator": "phone",
                    "data-required": "true",
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "h-4 w-4 rounded border-slate-300 dark:border-slate-600 text-primary-600 focus:ring-primary-500 bg-white dark:bg-slate-700"
                }
            ),
        }

    # ── Field-level validators ────────────────────────────────────────────────

    def clean_roll_no(self):
        roll_no = self.cleaned_data.get("roll_no")
        if roll_no is None:
            raise forms.ValidationError("Roll number is required.")
        if roll_no < 1:
            raise forms.ValidationError("Roll number must be at least 1.")
        if roll_no > 9999:
            raise forms.ValidationError("Roll number cannot exceed 9999.")
        return roll_no

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

    def clean_rfid_uid(self):
        rfid_uid = self.cleaned_data.get("rfid_uid", "").strip().upper()
        if not rfid_uid:
            raise forms.ValidationError("RFID UID is required.")
        if len(rfid_uid) < 4:
            raise forms.ValidationError("RFID UID must be at least 4 characters.")
        if len(rfid_uid) > 50:
            raise forms.ValidationError("RFID UID must be no more than 50 characters.")
        qs = Student.objects.filter(rfid_uid__iexact=rfid_uid)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("This RFID UID is already assigned to another student.")
        return rfid_uid

    def clean_contact(self):
        value = self.cleaned_data.get("contact", "").strip()
        if not value:
            return value
        if not _PHONE_RE.match(value):
            raise forms.ValidationError(
                "Enter a valid 10-digit number starting with 97 or 98."
            )
        return value

    def clean_guardian_name(self):
        value = self.cleaned_data.get("guardian_name", "").strip()
        if not value:
            raise forms.ValidationError("Guardian name is required.")
        if len(value) < 2:
            raise forms.ValidationError("Guardian name must be at least 2 characters.")
        if len(value) > 100:
            raise forms.ValidationError("Guardian name must be no more than 100 characters.")
        return value

    def clean_guardian_contact(self):
        value = self.cleaned_data.get("guardian_contact", "").strip()
        if not value:
            raise forms.ValidationError("Guardian contact number is required.")
        if not _PHONE_RE.match(value):
            raise forms.ValidationError(
                "Enter a valid 10-digit number starting with 97 or 98."
            )
        return value

    def clean_address(self):
        value = self.cleaned_data.get("address", "").strip()
        if len(value) > 500:
            raise forms.ValidationError("Address must be no more than 500 characters.")
        return value

    # ── Cross-field validator ─────────────────────────────────────────────────

    def clean(self):
        cleaned_data = super().clean()
        roll_no = cleaned_data.get("roll_no")
        classroom = cleaned_data.get("classroom")

        if roll_no is not None and classroom:
            qs = Student.objects.filter(classroom=classroom, roll_no=roll_no)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    f"Roll number {roll_no} is already assigned in classroom {classroom}."
                )

        return cleaned_data
