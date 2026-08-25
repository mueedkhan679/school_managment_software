import os
from decimal import Decimal
from django import forms
from django.core.exceptions import ValidationError

from apps.classrooms.models import SchoolClass
from .models import Gender, Student

# Allowed image extensions and max size (5 MB)
ALLOWED_IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"]
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


class StudentForm(forms.ModelForm):
    """Form for adding and editing Student records with security and validation."""

    class Meta:
        model = Student
        fields = [
            "name",
            "father_name",
            "school_class",
            "date_of_birth",
            "gender",
            "form_b_number",
            "email",
            "phone",
            "address",
            "photo",
            "custom_monthly_fee",
            "admission_fee",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Student's Full Name", "required": True}
            ),
            "father_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Father's Full Name", "required": True}
            ),
            "school_class": forms.Select(
                attrs={"class": "form-control", "required": True}
            ),
            "date_of_birth": forms.DateInput(
                attrs={"class": "form-control", "type": "date", "required": True}
            ),
            "gender": forms.Select(
                attrs={"class": "form-control", "required": True}
            ),
            "form_b_number": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g. 35201-1234567-1"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "e.g. student@gmail.com (optional)"}
            ),
            "phone": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g. 0300-1234567 (optional)"}
            ),
            "address": forms.Textarea(
                attrs={"class": "form-control", "rows": 3, "placeholder": "Residential Address (optional)"}
            ),
            "photo": forms.FileInput(
                attrs={"class": "form-control", "accept": "image/jpeg,image/png,image/webp"}
            ),
            "custom_monthly_fee": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Leave empty to use standard class fee",
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "admission_fee": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "One-time admission fee (optional)",
                    "step": "0.01",
                    "min": "0",
                }
            ),
        }
        labels = {
            "name": "Student Full Name *",
            "father_name": "Father's Name *",
            "school_class": "Class / Grade *",
            "date_of_birth": "Date of Birth *",
            "gender": "Gender *",
            "form_b_number": "Form-B / B-Form Number",
            "email": "Email / Gmail (Optional)",
            "phone": "Contact Phone Number (Optional)",
            "address": "Home Address (Optional)",
            "photo": "Passport Size Photo (Optional)",
            "custom_monthly_fee": "Custom Monthly Fee Override (Rs)",
            "admission_fee": "Admission Fee (Rs) - Optional",
        }
        help_texts = {
            "photo": "Supported formats: JPG, PNG, WEBP. Max size: 5MB.",
            "custom_monthly_fee": "Optional fee discount/override. If left blank, the class default monthly fee will apply.",
            "admission_fee": "One-time admission fee collected at registration. Leave blank if not applicable.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["school_class"].queryset = SchoolClass.objects.order_by("order", "id")

    def clean_admission_fee(self):
        fee = self.cleaned_data.get("admission_fee")
        if fee is not None and fee < Decimal("0.00"):
            raise ValidationError("Admission fee cannot be negative.")
        return fee

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")
        if photo and hasattr(photo, "size"):
            # Check file size
            if photo.size > MAX_IMAGE_SIZE_BYTES:
                raise ValidationError("Image file size must not exceed 5MB.")

            # Check file extension
            ext = os.path.splitext(photo.name)[1].lower()
            if ext not in ALLOWED_IMAGE_EXTENSIONS:
                raise ValidationError(
                    f"Unsupported file format '{ext}'. Allowed formats: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
                )
        return photo

    def clean_custom_monthly_fee(self):
        fee = self.cleaned_data.get("custom_monthly_fee")
        if fee is not None and fee < Decimal("0.00"):
            raise ValidationError("Custom monthly fee cannot be negative.")
        return fee
