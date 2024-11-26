import os

from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.core.mail import send_mail
from django.test import TestCase
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class EmailTests(TestCase):
    """Test cases for email functionality."""

    def setUp(self) -> None:
        """Set up test data"""
        self.user = User.objects.create_user(
            username="testuser",
            email=os.getenv("EMAIL_HOST_USER"),
            password="testpass123",
        )

    def test_email_settings(self) -> None:
        """Test email settings are configured correctly"""
        # Compare settings with .env values
        self.assertEqual(settings.EMAIL_HOST, os.getenv("EMAIL_HOST"))
        self.assertEqual(settings.EMAIL_PORT, int(os.getenv("EMAIL_PORT")))
        self.assertEqual(settings.EMAIL_HOST_USER, os.getenv("EMAIL_HOST_USER"))
        self.assertEqual(settings.DEFAULT_FROM_EMAIL, os.getenv("DEFAULT_FROM_EMAIL"))

    def test_send_email(self) -> None:
        """Test sending an email"""
        # Send test email using .env values
        subject = "Test Email"
        message = "This is a test email from BuildingCode AI"
        from_email = os.getenv("DEFAULT_FROM_EMAIL")
        recipient_list = [os.getenv("EMAIL_HOST_USER")]

        # Send the email
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=recipient_list,
                fail_silently=False,
            )
            self.assertEqual(len(mail.outbox), 1)
            sent_email = mail.outbox[0]
            self.assertEqual(sent_email.subject, subject)
            self.assertEqual(sent_email.body, message)
            self.assertEqual(sent_email.from_email, from_email)
            self.assertEqual(sent_email.to, recipient_list)

        except Exception as e:
            self.fail(f"Failed to send email: {str(e)}")
