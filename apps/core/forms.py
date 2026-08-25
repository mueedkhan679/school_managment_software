"""Forms for school-wide configuration."""
from django import forms

from .models import SchoolSettings


class SchoolSettingsForm(forms.ModelForm):
    """Configure global school branding (name, phone, logo).

    Rendered below the credentials fields on the Change Credentials page; the
    surrounding ``<form>`` must use ``enctype="multipart/form-data"`` so the
    logo image uploads correctly.
    """

    class Meta:
        model = SchoolSettings
        fields = ["school_name", "school_phone", "school_logo"]
        widgets = {
            "school_name": forms.TextInput(
                attrs={"class": "input", "placeholder": "e.g. Al-Noor Public School"}
            ),
            "school_phone": forms.TextInput(
                attrs={"class": "input", "placeholder": "e.g. 0300-1234567"}
            ),
            # ClearableFileInput keeps the previously-uploaded logo when the
            # form is re-posted without selecting a new file.
            "school_logo": forms.ClearableFileInput(
                attrs={"class": "input", "accept": "image/*"}
            ),
        }
