from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User


class CustomUserCreationForm(UserCreationForm):
    """Form for custom user creation."""

    email = forms.EmailField(required=True)

    class Meta:
        """Meta class for form configuration."""

        model = User
        fields = ("username", "email", "password1", "password2")

    def save(self, commit: bool = True) -> User:
        """Save the user instance.

        Args:
            commit: Whether to commit the changes to the database.

        Returns:
            The saved user instance.
        """
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user
