from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("", views.signin, name="signin"),
    path("register", views.signup, name="register"),
    path("verify-email/<slug:username>", views.verify_email, name="verify-email"),
    path("resend-otp", views.resend_otp, name="resend-otp"),
    path("login", views.signin, name="signin"),
    path("dashboard/", views.dashboard_view, name='dashboard'),
    path("logout", auth_views.LogoutView.as_view(next_page="login"), name='logout'),
    path('admin-dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path("single_upload/", views.single_upload_view, name="single_upload"),
    path('single_upload/<str:action>/', views.single_upload_handler, name='single_upload_action'),
    path('bulk_upload/', views.bulk_upload_view, name='bulk_upload'),
    path('accounts/login/', auth_views.LoginView.as_view(template_name="login.html"), name='login'),
    #path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('request-plan/', views.request_plan, name='request_plan'),
    path('approve-plan-request/<int:request_id>/', views.approve_plan_request_view, name='approve_plan_request'),
    path('reject-plan-request/<int:request_id>/', views.reject_plan_request_view, name='reject_plan_request'),
    path('purchase/',views.purchase_view,name='purchase'),
   
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
