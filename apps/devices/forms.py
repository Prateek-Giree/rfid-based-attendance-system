from django import forms
from .models import RFIDDevice
from apps.students.models import Classroom


class DeviceForm(forms.ModelForm):
    """
    Form for registering and updating RFID devices.
    Uses the current RFIDDevice database model.
    """

    classroom = forms.ModelChoiceField(
        queryset=Classroom.objects.all(),
        empty_label="Select Classroom",
        label="Assigned Classroom",
        widget=forms.Select(
            attrs={
                "class": "input-field",
                "data-validator": "required",
                "data-required": "true",
            }
        ),
    )

    is_active = forms.BooleanField(
        required=False,
        label="Device Status",
        initial=True,
        widget=forms.CheckboxInput(
            attrs={
                "class": "rounded border-slate-300 text-primary-600 focus:ring-primary-500 h-4 w-4",
            }
        ),
    )

    class Meta:
        model = RFIDDevice
        fields = ["name", "classroom", "is_active"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "input-field",
                    "placeholder": "e.g., Library RFID Reader",
                    "data-validator": "text-length",
                    "data-required": "true",
                    "data-min": "2",
                    "data-max": "100",
                }
            ),
        }

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        if not name:
            raise forms.ValidationError("Device name is required.")
        if len(name) < 2:
            raise forms.ValidationError("Device name must be at least 2 characters.")
        if len(name) > 100:
            raise forms.ValidationError("Device name must be no more than 100 characters.")
        return name

    def clean_classroom(self):
        classroom = self.cleaned_data.get("classroom")
        if not classroom:
            raise forms.ValidationError("Classroom assignment is required.")
        return classroom
