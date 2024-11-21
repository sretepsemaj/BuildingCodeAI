from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User

class ViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_home_view(self):
        """Test the home view is accessible"""
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/home.html')

    def test_login_view(self):
        """Test the login functionality"""
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after login

    def test_profile_view_protected(self):
        """Test that profile view requires authentication"""
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

        # Test after login
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/profile.html')
