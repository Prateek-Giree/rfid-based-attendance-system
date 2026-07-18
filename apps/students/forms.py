from django import forms
from .models import Classroom
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
