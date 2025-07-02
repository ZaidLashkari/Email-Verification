
from django.db import models
from django.contrib.auth.models import AbstractUser, User
from django.conf import settings
import random
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import timedelta, datetime
# Create your models here.

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    
    USERNAME_FIELD = ("email")
    REQUIRED_FIELDS = ["username"]
    
    def __str__(self):
        return self.email
    
class OtpToken(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='otp_token')
    otp_code = models.CharField(max_length=6, blank=True, editable=False)
    otp_expires_at = models.DateTimeField()

    def save(self, *args, **kwargs):
        # Generate OTP code if not already set
        if not self.otp_code:
            self.otp_code = str(random.randint(100000, 999999))  # 6-digit OTP
        super().save(*args, **kwargs)

    def is_expired(self):
        # Check if the OTP has expired
        return timezone.now() > self.otp_expires_at

    def __str__(self):
        return f"OTP for {self.user.username} - Expires at {self.otp_expires_at}"
    
 
class UserProfile(models.Model):
    coupon = models.ForeignKey('Coupon', on_delete=models.CASCADE, related_name="coupon",null=True,blank=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    credits = models.IntegerField(default=0)
    total_uploaded_files = models.IntegerField(default=0)  # Tracks the total uploads
    credits_expiry = models.DateTimeField(null=True, blank=True)  # Expiry date field


    def __str__(self):
        return f"Profile for {self.user.email}"


class UserActivity(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    activity = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Activity for {self.user.email} - {self.timestamp}"
    
# Agar plan ke upr user ko kuch limited Credits chahiye hone tb ye model ka use krna
class CreditRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="credit_requests")
    requested_credits = models.IntegerField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.requested_credits} credits ({self.status})"


#06-01-25
class UploadedFile(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    file = models.FileField(upload_to='uploads/')
    is_valid = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    upload_type = models.CharField(max_length=50, choices=[('single', 'Single'), ('bulk', 'Bulk')], default='single')  # Added this line

    def __str__(self):
        return f"File uploaded by {self.user.email} on {self.uploaded_at}"
    

class EmailRecord(models.Model):
    uploaded_file = models.ForeignKey(UploadedFile,null=True,blank=True, on_delete=models.CASCADE, related_name='email_records')
    user = models.ForeignKey(settings.AUTH_USER_MODEL,null=True, on_delete=models.CASCADE)
    email = models.EmailField()
    is_valid = models.BooleanField(null=True)  # Null until verified
    status = models.CharField(max_length=50, blank=True)  # Additional status messages
    verified_at = models.DateTimeField(null=True, blank=True)  # Timestamp of verification

    def __str__(self):
        return f"Email: {self.email} (Valid: {self.is_valid})"


#15-01-25
# Chalo pura naya model for plan
class Plan(models.Model):
    name = models.CharField(max_length=50, unique=True)
    credits = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.name} - {self.credits} credits (${self.price})"

# class PlanRequest(models.Model):
#     STATUS_CHOICES = [
#         ('PENDING', 'Pending'),
#         ('APPROVED', 'Approved'),
#         ('REJECTED', 'Rejected'),
#     ]

#     user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
#     plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
#     status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
#     requested_credits = models.PositiveIntegerField(default=0)
#     timestamp = models.DateTimeField(auto_now_add=True)

class PlanRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, null=True, blank=True)  # Optional for custom plans
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    requested_credits = models.PositiveIntegerField(default=0)
    custom_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_custom = models.BooleanField(default=False)  # Identify custom requests
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.is_custom:
            return f"Custom Plan Request by {self.user.username} - ${self.custom_price}"
        
        # Safely handle the case where plan might be None
        if self.plan:
            return f"{self.user.username} - {self.plan.name} (${self.plan.price})"
        
        return f"{self.user.username} - No Plan Assigned"


#01-02-25

class BillingDetail(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="billing_details")
    company_name = models.CharField(max_length=255, blank=True, null=True)
    billing_address = models.TextField(null=True)
    city = models.CharField(max_length=100,null=True, blank=True)
    state = models.CharField(max_length=100,null=True, blank=True)
    postal_code = models.CharField(max_length=20,null=True, blank=True)
    tax_id = models.CharField(max_length=100,null=True,blank=True)
    country = models.CharField(max_length=100,null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Billing Details for {self.user.email} - {self.country}, {self.city}"

    
class Coupon(models.Model):
    code = models.CharField(max_length=20, unique=True)
    discount_percentage = models.PositiveIntegerField()  # Discount in percentage
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    usage_limit = models.PositiveIntegerField(default=1)  # How many times a coupon can be used
    used_count = models.PositiveIntegerField(default=0)  # How many times it has been used

    def is_valid(self):
        """Check if the coupon is still valid"""
        now = timezone.now()
        return self.valid_from <= now <= self.valid_until and self.used_count < self.usage_limit

    def __str__(self):
        return f"Coupon {self.code} - {self.discount_percentage}% (Used {self.used_count}/{self.usage_limit})"
