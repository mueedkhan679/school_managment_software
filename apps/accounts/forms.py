"""Authentication forms for the School Management System."""
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError

User = get_user_model()

ERROR_CURRENT_PASSWORD = "Your current password is incorrect."
ERROR_USERNAME_TAKEN = "This username is already in use."
ERROR_PASSWORD_MISMATCH = "The two password fields didn't match."


class LoginForm(forms.Form):
    """Credentials form for the admin login page."""

    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Enter your username",
                "autocomplete": "username",
            }
        ),
    )
    password = forms.CharField(
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Enter your password",
                "autocomplete": "current-password",
            }
        ),
    )


class ChangeCredentialsForm(forms.Form):
    """Lets the logged-in admin change their username and/or password.

    The current password must always be verified before any change is applied.
    Password strength is validated with Django's configured validators, and new
    passwords are stored hashed (PBKDF2) by ``set_password``.
    """

    current_password = forms.CharField(
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
        label="Current Password",
    )
    username = forms.CharField(
        max_length=150,
        validators=[UnicodeUsernameValidator()],
        label="Username",
        widget=forms.TextInput(attrs={"autocomplete": "username"}),
    )
    new_password1 = forms.CharField(
        strip=False,
        required=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        label="New Password",
    )
    new_password2 = forms.CharField(
        strip=False,
        required=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        label="Confirm New Password",
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["username"].initial = user.username

    def clean_current_password(self):
        value = self.cleaned_data.get("current_password", "")
        if not self.user.check_password(value):
            raise ValidationError(ERROR_CURRENT_PASSWORD)
        return value

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.exclude(pk=self.user.pk).filter(username__iexact=username).exists():
            raise ValidationError(ERROR_USERNAME_TAKEN)
        return username

    def clean_new_password2(self):
        password1 = self.cleaned_data.get("new_password1")
        password2 = self.cleaned_data.get("new_password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError(ERROR_PASSWORD_MISMATCH)
        return password2

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("new_password1")
        if password1:
            # Runs Django's configured password validators (strength checks).
            validate_password(password1, user=self.user)
        return cleaned

    def save(self):
        """Apply username/password changes to the user (hashed password)."""
        user = self.user
        new_username = self.cleaned_data["username"]
        new_password = self.cleaned_data.get("new_password1")
        if new_username != user.username:
            user.username = new_username
        if new_password:
            user.set_password(new_password)  # PBKDF2-hashed before saving
        user.save()
        return user


class CreateUserAccountForm(forms.Form):
    """Create and link a system login account for a Student or Teacher.

    The role is inferred from the profile_type supplied at form construction.
    Passwords are hashed via PBKDF2 (Django default).
    """

    username = forms.CharField(
        max_length=150,
        validators=[UnicodeUsernameValidator()],
        label="Username *",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "e.g. stu_000001 or tch_000001", "autocomplete": "off"}
        ),
    )
    password1 = forms.CharField(
        label="Password *",
        strip=False,
        widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="Confirm Password *",
        strip=False,
        widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "new-password"}),
    )

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("This username is already taken. Please choose a different one.")
        return username

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            raise ValidationError("The two password fields didn't match.")
        if p1:
            validate_password(p1)
        return cleaned


class ResetPasswordForm(forms.Form):
    """Admin quick-reset of a Student or Teacher account password."""

    new_password1 = forms.CharField(
        label="New Password *",
        strip=False,
        widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "new-password"}),
    )
    new_password2 = forms.CharField(
        label="Confirm New Password *",
        strip=False,
        widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "new-password"}),
    )

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("new_password1")
        p2 = cleaned.get("new_password2")
        if p1 and p2 and p1 != p2:
            raise ValidationError("The two password fields didn't match.")
        if p1:
            validate_password(p1)
        return cleaned
