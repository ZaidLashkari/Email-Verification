from django.db.models.signals import post_save
from django.conf import settings
from django.dispatch import receiver
from .models import OtpToken, UploadedFile, EmailRecord
from django.core.mail import send_mail
from django.utils import timezone
import csv

# Signal to create UserProfile
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        # Import UserProfile here to avoid circular import
        from .models import UserProfile
        # Create UserProfile instance for the new user
        UserProfile.objects.create(user=instance)

# Signal to save UserProfile after User is saved
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_profile(sender, instance, **kwargs):
    instance.userprofile.save()


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_token(sender, instance, created, **kwargs):
    if created:
        if instance.is_superuser:
            pass  # Don't create OTP for superuser
        else:
            # Create OTP token if not already created
            otp_token, created = OtpToken.objects.get_or_create(
                user=instance,
                otp_expires_at=timezone.now() + timezone.timedelta(minutes=5)
            )

            if created:
                # OTP token was created, make user inactive for email verification
                instance.is_active = False
                instance.save()

            # Fetch OTP token for email
            otp = otp_token

            if otp and otp.otp_code:
                # Prepare email
                subject = "Email Verification"
                message = f"""
                    Hi {instance.username}, here is your OTP: {otp.otp_code}
                    It expires in 5 minutes. Use the link below to verify your email:
                    http://127.0.0.1:8000/verify-email/{instance.username}
                """
                sender_email = "lashkarizaid66@gmail.com"
                receiver_email = [instance.email]

                # Send email
                send_mail(
                    subject,
                    message,
                    sender_email,
                    receiver_email,
                    fail_silently=False,
                )
            else:
                print(f"Error: OTP code not found for user {instance.username}")


@receiver(post_save, sender=UploadedFile)
def create_email_records(sender, instance, created, **kwargs):
    if created and instance.file.name.endswith('.csv'):
        with open(instance.file.path, 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                email = row[0].strip() if row else ''
                if email:  # Skip empty rows
                    EmailRecord.objects.create(uploaded_file=instance, email=email)
 

#15-01
