import datetime
from django import forms
from apps.students.models import Classroom


class AttendanceFilterForm(forms.Form):
    """
    Used on the attendance list page for HTMX-driven filtering.
    Both fields are optional — omitting either shows all records.
    """

    classroom = forms.ModelChoiceField(
        queryset=Classroom.objects.all(),
        required=False,
        empty_label="All Classrooms",
        label="Classroom",
        widget=forms.Select(
            attrs={
                "class": "input-field",
                "hx-get": "",
                "hx-trigger": "change",
                "hx-target": "#attendance-table-container",
                "hx-include": "closest form",
            }
        ),
    )

    date = forms.DateField(
        required=False,
        label="Date",
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "input-field",
                "hx-get": "",
                "hx-trigger": "change",
                "hx-target": "#attendance-table-container",
                "hx-include": "closest form",
            }
        ),
        input_formats=["%Y-%m-%d"],
    )


class AttendanceMarkForm(forms.Form):
    """
    Controls the classroom + date selection header of the manual mark page.
    Validated before the student roster is rendered.
    """

    classroom = forms.ModelChoiceField(
        queryset=Classroom.objects.all(),
        required=True,
        empty_label="Select Classroom",
        label="Classroom",
        widget=forms.Select(attrs={"class": "input-field", "data-validator": "required", "data-required": "true"}),
    )

    date = forms.DateField(
        required=True,
        label="Date",
        initial=datetime.date.today,
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "input-field",
                "data-validator": "required",
                "data-required": "true",
            }
        ),
        input_formats=["%Y-%m-%d"],
    )

    def clean_classroom(self):
        classroom = self.cleaned_data.get("classroom")
        if not classroom:
            raise forms.ValidationError("Please select a classroom.")
        return classroom

    def clean_date(self):
        date = self.cleaned_data.get("date")
        if not date:
            raise forms.ValidationError("Please select a date.")
        if date > datetime.date.today():
            raise forms.ValidationError("Cannot mark attendance for a future date.")
        return date
