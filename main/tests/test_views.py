from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse


class ViewTests(TestCase):
    """Test cases for the views module."""

    def setUp(self) -> None:
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_home_view(self) -> None:
        """Test the home page view."""
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "main/home.html")

    def test_login_required(self) -> None:
        """Test the login required view."""
        # Try accessing profile without login
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, 302)  # Should redirect to login

        # Login and try again
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, 200)
