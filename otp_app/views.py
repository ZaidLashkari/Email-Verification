from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import get_user_model, authenticate, login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from django.utils.timezone import localtime
from django.core.mail import send_mail
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.base import ContentFile
from django.core.paginator import Paginator
from io import TextIOWrapper
import csv
import os
import pandas as pd

from .forms import RegisterForm, SingleUploadForm, BulkUploadForm
from .models import OtpToken, UploadedFile, UserProfile, UserActivity, Plan, PlanRequest
from .utils import is_valid_email
from django.conf import settings

from datetime import timedelta
from django.utils.timezone import now
from celery import shared_task
from django.utils.timezone import now

# Utility function to get or create a UserProfile
def get_or_create_user_profile(user):
    try:
        return UserProfile.objects.get(user=user)
    except ObjectDoesNotExist:
        return UserProfile.objects.create(user=user, credits=0)


# Utility function to send OTP email
def send_otp_email(user):
    otp = OtpToken.objects.create(user=user, otp_expires_at=timezone.now() + timezone.timedelta(minutes=5))
    
    subject = "Email Verification"
    message = f"""
        Hi {user.username}, here is your OTP {otp.otp_code} 
        it expires in 5 minutes, use the URL below to redirect back to the website
        http://127.0.0.1:8000/verify-email/{user.username}
    """
    sender = "lashkarizaid66@gmail.com"
    receiver = [user.email, ]
    
    # Send email
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        receiver,
        fail_silently=False,
    )
    return otp

# Index view
def index(request):
    return render(request, "index.html")


# Sign-up view
def signup(request):
    form = RegisterForm()
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account created successfully! An OTP was sent to your Email")
            return redirect("verify-email", username=request.POST['username'])
    context = {"form": form}
    return render(request, "signup.html", context)


# Verify email view
def verify_email(request, username):
    user = get_user_model().objects.get(username=username)
    user_otp = OtpToken.objects.filter(user=user).last()

    if request.method == 'POST':
        # valid token
        if user_otp.otp_code == request.POST['otp_code']:
            # checking for expired token
            if user_otp.otp_expires_at > timezone.now():
                user.is_active = True
                user.save()
                messages.success(request, "Account activated successfully!! You can Login.")
                return redirect("signin")
            # expired token
            else:
                messages.warning(request, "The OTP has expired, get a new OTP!")
                return redirect("verify-email", username=user.username)

        # invalid otp code
        else:
            messages.warning(request, "Invalid OTP entered, enter a valid OTP!")
            return redirect("verify-email", username=user.username)

    context = {}
    return render(request, "verify_token.html", context)


# Resend OTP view
def resend_otp(request):
    if request.method == 'POST':
        user_email = request.POST["otp_email"]

        if get_user_model().objects.filter(email=user_email).exists():
            user = get_user_model().objects.get(email=user_email)

            # Check if the user already has an OTP
            existing_otp = OtpToken.objects.filter(user=user).last()
            if existing_otp:
                # Optionally delete the old OTP before sending a new one
                existing_otp.delete()

            # Send a new OTP
            send_otp_email(user)
            messages.success(request, "A new OTP has been sent to your email-address")
            return redirect("verify-email", username=user.username)
        else:
            messages.warning(request, "This email doesn't exist in the database")
            return redirect("resend-otp")

    context = {}
    return render(request, "resend_otp.html", context)

# Sign-in view
def signin(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f"Hi {request.user.username}, you are now logged-in")
            return redirect("dashboard")

        else:
            messages.warning(request, "Invalid credentials")
            return redirect("signin")

    return render(request, "login.html", {
        'show_sidebar': False
        })



# Dashboard view
@login_required
def dashboard_view(request):
    if request.user.is_superuser:
        # If the user is an admin, redirect to the admin dashboard
        return redirect('admin_dashboard')
    else:
        # Regular user dashboard logic   single upload url vo upr link ke liye
        # single_upload_url = reverse('single_upload_action', kwargs={'action': 'dashboard'})
       #upar wala
        user_profile = get_or_create_user_profile(request.user)
        activities = UserActivity.objects.filter(user=request.user).order_by('-timestamp')
        approved_plan_request = request.user.planrequest_set.filter(status='APPROVED').last()
        return render(request, 'dashboard.html', {
            'user_profile': user_profile,
            'activities': activities,
            'show_sidebar': True,
            
            'approved_plan_request': approved_plan_request,
            # 'single_upload_url': single_upload_url,
        })

# Admin check function
def is_admin(user):
    return user.is_superuser


# Admin dashboard view
@login_required
@user_passes_test(is_admin)
def admin_dashboard_view(request):
    plan_requests = PlanRequest.objects.filter(status='PENDING')  # Get only pending requests
    return render(request, 'admin_dashboard.html', {'plan_requests': plan_requests})


#06-01-25

#01-11-25
# Lets Seperate the views:
def single_upload_handler(request, action):
    if action == "login":
        return signin(request)
    elif action == "logout":
        return signin(request)
    elif action == "dashboard":
        return dashboard_view(request)
    elif action == "bulk_upload":
        return bulk_upload_view(request)
    # sochna hoga
    # elif action == "request_plan":
    #      return request_plan(request)
    else:
        # Handle invalid action
        return render(request, "404.html", status=404)

def single_upload_view(request):
    single_form = SingleUploadForm()

    if request.method == 'POST':
        user = request.user
        user_profile = UserProfile.objects.get(user=user)

        single_form = SingleUploadForm(request.POST)
        if single_form.is_valid():
            email = single_form.cleaned_data['single_input']

            if is_valid_email(email):  # Check if email is valid
                if user_profile.credits > 5:
                    UploadedFile.objects.create(
                        user=user,
                        file=ContentFile(email, name=f'{user.username}_single.txt'),
                        is_valid=True,
                        upload_type='single' #added line 22
                        
                    )
                    user_profile.credits -= 5
                    user_profile.save()
                    messages.success(request, f"Email '{email}' is Valid !")
                else:
                    messages.error(request, "Insufficient credits.")
            else:
                UploadedFile.objects.create(
                    user=user,
                    file=ContentFile(email, name=f'{user.username}_single_invalid.txt'),
                    is_valid=False,
                    upload_type='single' #added line
                )
                user_profile.credits -= 5
                user_profile.save()
                messages.error(request, f"Invalid email: {email}")

            return redirect('single_upload')

    files_list = UploadedFile.objects.filter(user=request.user, upload_type='single').order_by('-uploaded_at')
    paginator = Paginator(files_list, 5)  # Show 10 files per page
    page_number = request.GET.get('page')
    files = paginator.get_page(page_number)

    return render(request, 'single_upload.html', {
        'single_form': single_form,
        'files': files,
        'show_sidebar': True
    })

#26-01-25 new bulk view
def bulk_upload_view(request):
    bulk_form = BulkUploadForm()
    results = []

    if request.method == 'POST':
        user = request.user
        user_profile = UserProfile.objects.get(user=user)

        bulk_form = BulkUploadForm(request.POST, request.FILES)
        if bulk_form.is_valid():
            bulk_text = bulk_form.cleaned_data.get('bulk_text', '')
            bulk_file = bulk_form.cleaned_data.get('bulk_file')

            emails = []

            # Extract emails from text input (if provided)
            if bulk_text:
                emails.extend(bulk_text.splitlines())

            # Extract emails from CSV file (if provided)
            if bulk_file:
                if bulk_file.name.endswith('.csv'):
                    csv_file = TextIOWrapper(bulk_file.file, encoding='utf-8')
                    reader = csv.reader(csv_file)
                    for row in reader:
                        if row:  # Skip empty rows
                            emails.append(row[0].strip())
                else:
                    messages.error(request, "Please upload a valid CSV file.")
                    return redirect('bulk_upload')

            # Check if credits are sufficient
            total_emails = len(emails)
            if user_profile.credits < 20:
                messages.error(
                    request,
                    f"Insufficient credits. You need {total_emails - user_profile.credits} more credits to verify all emails."
                )
                return redirect('bulk_upload')

            # Process emails
            valid_emails = []
            invalid_emails = []

            for email in emails:
                email = email.strip()
                if email:
                    result = is_valid_email(email)
                    results.append({'Email': email, 'Status': result})

                    # Categorize emails
                    if result:
                        valid_emails.append(email)
                    else:
                        invalid_emails.append(email)

            # Deduct credits for valid emails only
            user_profile.credits -= 20
            user_profile.save()

            # Save results to a CSV file
            csv_file_name = f"{user.username}_results.csv"
            full_file_path = os.path.join(settings.MEDIA_ROOT, csv_file_name)
            df = pd.DataFrame(results)
            df.to_csv(full_file_path, index=False)

            # Save the processed CSV in the backend
            uploaded_file = UploadedFile.objects.create(
                user=user,
                file=ContentFile(df.to_csv(index=False), name=csv_file_name),
                is_valid=True,
                upload_type='bulk'
            )

            # Record the time of upload (in UTC)
            upload_time = timezone.now()

            # Convert to IST
            upload_time_ist = localtime(upload_time)  # Convert to local timezone (Asia/Kolkata)

            # Format the time as per your requirements
            upload_time_str = upload_time_ist.strftime('%Y-%m-%d %H:%M:%S')

            # Generate a file URL for download
            bulk_csv_url = f"{settings.MEDIA_URL}{csv_file_name}"

            # Store the file details in the session for rendering the download button
            request.session['bulk_upload_details'] = {
                'user_name': user.username,
                'csv_filename': csv_file_name,
                'upload_time': upload_time_str,
                'bulk_csv_url': bulk_csv_url
            }
            messages.success(request, "File uploaded successfully. You can download it below.")
            
    bulk_upload_details = request.session.get('bulk_upload_details', None)
    files_list = UploadedFile.objects.filter(user=request.user, upload_type='bulk').order_by('-uploaded_at')
    paginator = Paginator(files_list, 5)  # Show 5 files per page
    page_number = request.GET.get('page')
    files = paginator.get_page(page_number)

    return render(request, 'bulk_upload.html', {
        'bulk_form': bulk_form,
        'bulk_upload_details': bulk_upload_details,
        'files': files,
        'show_sidebar': True,
    })






#15-01-25 9.16.pm

# Utility function to update plan request status
# 16-02-25
# @login_required
# @user_passes_test(is_admin)
# def approve_plan_request_view(request, request_id):
#     try:
#         planrequest_set = PlanRequest.objects.get(id=request_id)
#     except PlanRequest.DoesNotExist:
#         messages.error(request, "The plan request was not found.")
#         return redirect('admin_dashboard')

#     if planrequest_set.status == 'PENDING':
#         planrequest_set.status = 'APPROVED'
#         planrequest_set.save()

#         # Add credits to the user's profile when the plan is approved
#         user_profile = get_or_create_user_profile(planrequest_set.user)
#         user_profile.credits += planrequest_set.plan.credits
#         #user_profile.credits_expiry = now()+timedelta(days=60)
#         user_profile.save()

#         messages.success(request, f"Plan request for {planrequest_set.plan.name} from {planrequest_set.user.email} has been approved.")
#     return redirect('admin_dashboard')



# @login_required
# @user_passes_test(is_admin)
# def reject_plan_request_view(request, request_id):
#     try:
#         plan_request = PlanRequest.objects.get(id=request_id)
#     except PlanRequest.DoesNotExist:
#         messages.error(request, "The plan request was not found.")
#         return redirect('admin_dashboard')

#     if plan_request.status == 'PENDING':
#         plan_request.status = 'REJECTED'
#         plan_request.save()
#         messages.success(request, f"Plan request from {plan_request.user.email} has been rejected.")
#     return redirect('admin_dashboard')



# # Handle requesting a plan
# def request_plan(request):
#     if request.method == "POST":
#         plan_id = request.POST.get("plan_id")

#         if not plan_id:
#             return render(request, "request_plan.html", {"error": "Please select a valid plan."})

#         plan = get_object_or_404(Plan, id=plan_id)

#         # Create a plan request for the user
#         PlanRequest.objects.create(user=request.user, plan=plan)
#         messages.success(request, f"You have requested the {plan.name} plan.")
#         return redirect("dashboard")  # Redirect to the user dashboard after submitting the request

#     plans = Plan.objects.all()
#     return render(request, "request_plan.html", {"plans": plans, "show_sidebar":True})

# def purchase_view(request):
#    return render(request, "purchase.html")


# Check if the user is an admin
def is_admin(user):
    return user.is_staff

# Approve Plan Request
@login_required
@user_passes_test(is_admin)
def approve_plan_request_view(request, request_id):
    try:
        plan_request = PlanRequest.objects.get(id=request_id)
    except PlanRequest.DoesNotExist:
        messages.error(request, "The plan request was not found.")
        return redirect('admin_dashboard')

    if plan_request.status == 'PENDING':
        plan_request.status = 'APPROVED'
        plan_request.save()

        # Add credits to user profile
        user_profile = get_or_create_user_profile(plan_request.user)

        if hasattr(plan_request, "plan") and plan_request.plan:
            user_profile.credits += plan_request.plan.credits  # Standard Plan
        else:
            user_profile.credits += plan_request.requested_credits  # Custom Plan

        user_profile.save()
        messages.success(request, f"Plan request from {plan_request.user.email} has been approved.")
    
    return redirect('admin_dashboard')

# Reject Plan Request
@login_required
@user_passes_test(is_admin)
def reject_plan_request_view(request, request_id):
    try:
        plan_request = PlanRequest.objects.get(id=request_id)
    except PlanRequest.DoesNotExist:
        messages.error(request, "The plan request was not found.")
        return redirect('admin_dashboard')

    if plan_request.status == 'PENDING':
        plan_request.status = 'REJECTED'
        plan_request.save()
        messages.success(request, f"Plan request from {plan_request.user.email} has been rejected.")
    
    return redirect('admin_dashboard')

# Handle requesting a plan (including custom plan)
@login_required
def request_plan(request):
    if request.method == "POST":
        plan_id = request.POST.get("plan_id")
        custom_price = request.POST.get("custom_price")
        custom_credits = request.POST.get("custom_credits")

        if plan_id:  # Standard plan
            plan = get_object_or_404(Plan, id=plan_id)
            PlanRequest.objects.create(user=request.user, plan=plan)
            messages.success(request, f"You have requested the {plan.name} plan.")
        else:  # Custom plan
            if not custom_price or not custom_credits:
                messages.error(request, "Invalid custom plan request.")
                return redirect("request_plan")

            PlanRequest.objects.create(
                user=request.user,
                requested_credits=int(custom_credits),
                status="PENDING"
            )
            messages.success(request, "Your custom plan request has been sent to the admin.")

        return redirect("dashboard")

    plans = Plan.objects.all()
    return render(request, "request_plan.html", {"plans": plans, "show_sidebar": True})

# Purchase Page View
def purchase_view(request):
    return render(request, "purchase.html")