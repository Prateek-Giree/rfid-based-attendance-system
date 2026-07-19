from django import forms
from .models import Classroom, Student
from apps.auth_core.models import Teacher


class ClassroomForm(forms.ModelForm):
    """
    Form for creating and updating Classrooms.
    Uses Tailwind CSS components defined in the base layout.
    """

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
                }
            ),
            "section": forms.TextInput(
                attrs={
                    "class": "input-field",
                    "placeholder": "e.g., A",
                    "autocomplete": "off",
                }
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get("name")
        section = cleaned_data.get("section")

        # Check for unique_together constraint manually to present a nice validation message
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
    """
    Form for student registration and editing.
    Styled with Tailwind CSS input classes.
    """

    classroom = forms.ModelChoiceField(
        queryset=Classroom.objects.all(),
        empty_label="Select Classroom",
        label="Classroom",
        widget=forms.Select(attrs={"class": "input-field"}),
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
                }
            ),
            "first_name": forms.TextInput(
                attrs={"class": "input-field", "placeholder": "John"}
            ),
            "last_name": forms.TextInput(
                attrs={"class": "input-field", "placeholder": "Doe"}
            ),
            "rfid_uid": forms.TextInput(
                attrs={
                    "class": "input-field font-mono",
                    "placeholder": "e.g., A1B2C3D4",
                }
            ),
            "contact": forms.TextInput(
                attrs={"class": "input-field", "placeholder": "e.g., +977 98XXXXXXXX"}
            ),
            "address": forms.Textarea(
                attrs={
                    "class": "input-field h-20 resize-none",
                    "placeholder": "Enter street address...",
                }
            ),
            "guardian_name": forms.TextInput(
                attrs={"class": "input-field", "placeholder": "Jane Doe"}
            ),
            "guardian_contact": forms.TextInput(
                attrs={"class": "input-field", "placeholder": "e.g., +977 98XXXXXXXX"}
            ),
            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "h-4 w-4 rounded border-slate-300 dark:border-slate-600 text-primary-600 focus:ring-primary-500 bg-white dark:bg-slate-700"
                }
            ),
        }

    def clean_rfid_uid(self):
        rfid_uid = self.cleaned_data.get("rfid_uid")
        if rfid_uid:
            rfid_uid = rfid_uid.strip()
            # Enforce unique RFID UID manually for descriptive feedback
            qs = Student.objects.filter(rfid_uid__iexact=rfid_uid)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("This RFID UID is already assigned to another student.")
        return rfid_uid

    def clean(self):
        cleaned_data = super().clean()
        roll_no = cleaned_data.get("roll_no")
        classroom = cleaned_data.get("classroom")

        # Enforce unique roll number in classroom
        if roll_no is not None and classroom:
            qs = Student.objects.filter(classroom=classroom, roll_no=roll_no)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    f"Roll number {roll_no} is already assigned in classroom {classroom}."
                )

        return cleaned_data
